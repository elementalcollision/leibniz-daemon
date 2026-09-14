import Lean
open Lean Core

/-! # Report the axiom footprint AND the DENOTATION of the minted declaration.

    ## Axioms (ADR 0097 round 7)

    Earlier versions asked about ONE declaration, named from `theorem_src` by a Python regex. Every
    version of that regex diverged from Lean's parser somewhere, and the divergences were soundness
    holes: `theorem «id».foo` parsed as `«id»`, which resolves to core `id` -- clean and axiom-free
    -- while Lean declared the dirty `id.foo`. So the axiom question is asked of EVERY constant the
    module declares and there is no target to mis-aim.

    ## Denotation (ADR 0100)

    A clean axiom closure does not mean the statement says what it appears to say. Measured on the
    pin, `notation "False" => True` lets `theorem oops : False := trivial` elaborate reporting NO
    axioms at all -- an empty closure, cleaner than a legitimate proof. The kernel is not wrong:
    it proved exactly the proposition it was handed. What changed is which proposition that was.

    The compiled `Expr` has already resolved every notation and every name, so the DENOTATION is
    readable straight off the olean -- no parser-table diff, no name resolution reimplemented in
    Python, nothing to keep in sync with Lean's grammar.

    ## Why `loadExts := false` is load-bearing, not an optimisation

    Measured: importing with `loadExts := true` RUNS the module's initializers, so a preamble
    carrying `initialize (IO.Process.exit 0 : IO Unit)` kills this process -- it prints nothing and
    exits 0, and a caller keying on the exit code accepts the attack. A preamble `run_cmd` can go
    further and forge this tool's own success line on its real stdout, reading the nonce out of
    `ps -o args= -p $PPID`; a nonce protocol does not save a design that runs the adversary's code.
    At `loadExts := false` the same olean reads safely. NEVER raise this flag. -/

/-- Constants a preamble adds are not internal detail; `_sunfold` etc. are. -/
private def interesting (env : Environment) (idx : ModuleIdx) (n : Name) : Bool :=
  env.getModuleIdxFor? n == some idx && !n.isInternal

def main (args : List String) : IO UInt32 := do
  match args with
  | [modName, nonce, expectedPath] =>
    initSearchPath (← findSysroot)
    let mod := modName.toName
    -- The expected declaration name arrives as a FILE, never as argv or a shell word: round 7
    -- found the theorem name was both a shell-injection vector and a way to mis-aim the question.
    let expected ← try pure (← IO.FS.readFile expectedPath).trimAscii.toString
                   catch _ => pure ""
    if expected.isEmpty then
      IO.println s!"{nonce} EXPECTED-MISSING"; return 1
    let env ← importModules #[{ module := mod }] {} (loadExts := false)
    match env.header.moduleNames.findIdx? (· == mod) with
    | none => IO.println s!"{nonce} MISSING {modName}"; return 1
    | some idx =>
      let ours := env.constants.fold (init := #[]) fun acc n _ =>
        if interesting env idx n then acc.push n else acc
      if ours.isEmpty then IO.println s!"{nonce} EMPTY {modName}"; return 1

      -- 1. AXIOMS -- unchanged protocol, every declared constant, no target to mis-aim.
      let mut all : NameSet := {}
      for c in ours do
        let (axs, _) ← (Lean.collectAxioms c : CoreM (Array Name)).toIO
            { fileName := "<axcheck>", fileMap := default } { env := env }
        for a in axs do all := all.insert a
      let names := all.toList.map toString
      IO.println s!"{nonce} AXIOMS {ours.size} [{", ".intercalate names}]"

      -- 2. ROOT -- locate the minted declaration. It normally lands at exactly the name its
      --    source wrote; a preamble that leaves `namespace Foo` open makes it land at `Foo.<name>`.
      --    That ALONE is not an attack -- an operator preamble may legitimately open a namespace
      --    and never close it (round 6 pinned `namespace LeibNS` as an honest shape) -- so a
      --    nested landing is reported, not refused. Missing entirely fails CLOSED, which is why
      --    reintroducing the name is safe where round 7's mis-aimable probe was not: a wrong name
      --    reads as "absent" and REFUSES, it does not report cleanly on a decoy.
      let want := expected.toName
      let exact := ours.find? (· == want)
      let nested := ours.find? fun n => n != want && (n.replacePrefix n.getPrefix .anonymous) == want
      let some decl := exact.orElse (fun _ => nested)
        | IO.println s!"{nonce} ROOT MISSING {expected}"; return 0
      let nsPrefix := decl.getPrefix
      IO.println s!"{nonce} ROOT {if exact.isSome then "OK" else "NESTED"} {decl}"

      match env.find? decl with
      | none => IO.println s!"{nonce} DENOTE-MISSING"; return 0
      | some ci =>
        let consts := (ci.type.foldConsts ({} : NameSet) fun c s => s.insert c).toList
        -- 3. SHADOW -- what actually makes the shadowing attack work. Inside an open `namespace
        --    Foo`, a preamble `def False` resolves AHEAD of core `False`, so `theorem oops : False`
        --    proves `Foo.False`. The signature is a constant in the STATEMENT's type that this
        --    module declared under the landing namespace AND whose bare name already names a
        --    DIFFERENT constant. Honest preambles name their own constants freely (a real law's
        --    type mentions six of them) -- what none of them do is collide with an existing name.
        --    Measured: with scopes balanced Lean itself refuses every shadowing spelling
        --    ("Ambiguous term", "has already been declared"), so this is the whole live surface.
        let shadows := consts.filter fun c =>
          nsPrefix != .anonymous && interesting env idx c && nsPrefix.isPrefixOf c &&
            (let bare := c.replacePrefix nsPrefix .anonymous
             bare != c && env.contains bare)
        if !shadows.isEmpty then
          IO.println s!"{nonce} SHADOW [{", ".intercalate (shadows.map toString)}]"
          return 0
        IO.println s!"{nonce} SHADOW []"
        let cs := consts.map toString
        IO.println s!"{nonce} DENOTE [{", ".intercalate cs.toArray.qsort.toList}]"
        -- 4. VACUOUS -- the statement type IS `True`. Every measured syntax attack collapses to
        --    this, and an honest law proving `True` is worthless anyway, so refusing costs nothing.
        IO.println s!"{nonce} VACUOUS {if ci.type.isConstOf ``True then "yes" else "no"}"
        return 0
  | _ => IO.eprintln "usage: axcheck <module> <nonce> <expected-name-file>"; return 2
