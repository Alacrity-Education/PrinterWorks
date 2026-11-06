#!/usr/bin/env python3
"""CFG-based max-stack analyser for SDCC/STM8 .asm output.

For each function we build a basic-block-free instruction list, then run a
worklist dataflow over the control-flow graph tracking SP depth, so branches
and tail-calls do not corrupt the running total (the naive linear walk does).
Call sites contribute sp_at_call + 2 (CALL pushes a 2-byte return address)
plus the callee's own max chain, resolved recursively over the call graph.

Usage: stackscan.py file1.asm [file2.asm ...]
"""
import re
import sys

FUNC_RE = re.compile(r'^(_[A-Za-z_][A-Za-z0-9_]*):\s*$')
LOCLBL_RE = re.compile(r'^(\d+\$):\s*$')
SUBSP_RE = re.compile(r'^\s*sub\s+sp,\s*#(\d+)\s*$')
ADDSP_RE = re.compile(r'^\s*addw\s+sp,\s*#(\d+)\s*$')
CALL_RE = re.compile(r'^\s*call(?:f)?\s+(_[A-Za-z_][A-Za-z0-9_]*)\s*$')
JPFUNC_RE = re.compile(r'^\s*jp\s+(_[A-Za-z_][A-Za-z0-9_]*)\s*$')
JMP_RE = re.compile(r'^\s*(jra|jp|jrt)\s+(\d+\$)\s*$')
CJMP_RE = re.compile(r'^\s*(jr[a-z]+)\s+(\d+\$)\s*$')
BTJ_RE = re.compile(r'^\s*(btjt|btjf)\s+.*,\s*(\d+\$)\s*$')
RET_RE = re.compile(r'^\s*(ret|retf|iret)\s*$')
JPX_RE = re.compile(r'^\s*jp\s+\((x|y)\)\s*$')

# SDCC stm8 runtime helpers: own max stack use (excluding their return address).
LIB = {
    '__mulint': 4, '__modsint': 8, '__divsint': 8,
    '__divuint': 2, '__moduint': 2,
    '___sdcc_external_startup': 0, '_cap_code': 0,
}


def load(paths):
    """Return {func_name: [instruction strings]} preserving order."""
    funcs = {}
    cur = None
    for path in paths:
        for raw in open(path):
            line = raw.rstrip('\n')
            if not line.strip() or line.lstrip().startswith(';'):
                continue
            m = FUNC_RE.match(line)
            if m:
                cur = m.group(1)
                funcs[cur] = []
                continue
            if line.startswith('\t.area') or line.startswith('\t.globl'):
                continue
            if cur is not None:
                funcs[cur].append(line)
    # Drop data labels (no instructions with sp/ret semantics at all)
    return {k: v for k, v in funcs.items() if v}


# Stack bytes of arguments each callee pops on return (callee-cleanup).
# Filled in by main() from each function's epilogue before the CFG walk.
ARGS = {'__mulint': 2, '__modsint': 2, '__divsint': 2}


def arg_cleanup(body, frame):
    """SDCC stm8 epilogues:
         ldw x,(k,sp) / addw sp,#M / jp (x)   -> M = frame + 2 + args
         addw sp,#M / ret                     -> args = 0
    """
    best = 0
    for i, ins in enumerate(body):
        if not JPX_RE.match(ins):
            continue
        for j in (i - 1, i - 2):
            if j < 0:
                continue
            m = ADDSP_RE.match(body[j])
            if m:
                best = max(best, int(m.group(1)) - frame - 2)
                break
    return max(best, 0)


def analyse(body):
    """Return (own_peak, [(callee, sp_at_call), ...]) via CFG worklist."""
    labels = {}
    for i, ins in enumerate(body):
        m = LOCLBL_RE.match(ins)
        if m:
            labels[m.group(1)] = i
    peak = 0
    calls = []
    seen = {}
    work = [(0, 0)]
    budget = 400000
    while work:
        pc, sp = work.pop()
        while True:
            budget -= 1
            if budget <= 0 or pc >= len(body) or sp > 400 or sp < -64:
                break
            if seen.get(pc, -1) >= sp:
                break
            seen[pc] = sp
            ins = body[pc]
            peak = max(peak, sp)

            m = SUBSP_RE.match(ins)
            if m:
                sp += int(m.group(1)); peak = max(peak, sp); pc += 1; continue
            m = ADDSP_RE.match(ins)
            if m:
                sp -= int(m.group(1)); pc += 1; continue
            s = ins.strip()
            if s.startswith('pushw'):
                sp += 2; peak = max(peak, sp); pc += 1; continue
            if s.startswith('push'):
                sp += 1; peak = max(peak, sp); pc += 1; continue
            if s.startswith('popw'):
                sp -= 2; pc += 1; continue
            if s.startswith('pop'):
                sp -= 1; pc += 1; continue

            m = CALL_RE.match(ins)
            if m:
                calls.append((m.group(1), sp))
                # SDCC stm8 is callee-cleanup: the callee's epilogue pops the
                # stack-passed arguments the caller just pushed.
                sp -= ARGS.get(m.group(1), 0)
                pc += 1; continue
            m = JPFUNC_RE.match(ins)
            if m:                       # tail call: no extra return address
                calls.append((m.group(1), sp - 2)); break
            if JPX_RE.match(ins):
                # switch dispatch:  ldw x,(#00181$, x) / jp (x)
                m2 = re.match(r'^\s*ldw\s+x,\s*\(#(\d+\$),\s*x\)',
                              body[pc - 1] if pc else '')
                if m2 and m2.group(1) in labels:
                    k = labels[m2.group(1)] + 1
                    while k < len(body):
                        m3 = re.match(r'^\s*\.dw\s+#(\d+\$)', body[k])
                        if not m3:
                            break
                        if m3.group(1) in labels:
                            work.append((labels[m3.group(1)], sp))
                        k += 1
                break
            if RET_RE.match(ins):
                break
            m = JMP_RE.match(ins)
            if m:
                nxt = labels.get(m.group(2))
                if nxt is None:
                    break
                pc = nxt; continue
            m = CJMP_RE.match(ins) or BTJ_RE.match(ins)
            if m:
                tgt = labels.get(m.group(2))
                if tgt is not None:
                    work.append((tgt, sp))
                pc += 1; continue
            pc += 1
    return peak, calls


def main():
    funcs = load(sys.argv[1:])
    frames = {}
    for name, body in funcs.items():
        frame = 0
        for ins in body[:2]:
            m = SUBSP_RE.match(ins)
            if m:
                frame = int(m.group(1))
            elif ins.strip().startswith('pushw'):
                frame = 2
        frames[name] = frame
        ARGS[name] = arg_cleanup(body, frame)
    info = {}
    for name, body in funcs.items():
        peak, calls = analyse(body)
        info[name] = {'peak': peak, 'calls': calls, 'frame': frames[name],
                      'args': ARGS[name]}

    memo = {}

    def chain(name, stack):
        if name in LIB:
            return LIB[name]
        if name not in info:
            return 0
        if name in stack:
            return 0
        if name in memo:
            return memo[name]
        f = info[name]
        best = f['peak']
        for callee, sp_at in f['calls']:
            best = max(best, sp_at + 2 + chain(callee, stack | {name}))
        memo[name] = best
        return best

    print(f"{'function':26s} {'frame':>6s} {'args':>5s} {'own peak':>9s} "
          f"{'max chain':>10s}  worst callee")
    for n in sorted(info):
        deep = ''
        f = info[n]
        if not f['peak'] and not f['calls'] and not f['frame']:
            continue                      # data label, not code
        best = -1
        for callee, sp_at in f['calls']:
            v = sp_at + 2 + chain(callee, {n})
            if v > best:
                best, deep = v, callee
        print(f"{n:26s} {f['frame']:6d} {f['args']:5d} {f['peak']:9d} "
              f"{chain(n, set()):10d}  {deep if best >= f['peak'] else ''}")


if __name__ == '__main__':
    main()
