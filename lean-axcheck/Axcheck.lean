import Lean
open Lean Core

/-- Report the UNION of the axiom closures of every constant module `mod` declares.

    ADR 0097 round 7. Earlier versions asked about ONE declaration, named from `theorem_src` by a
    Python regex. Every version of that regex diverged from Lean's parser somewhere, and the
    divergences were soundness holes, not nuisances: `theorem «id».foo` parsed as `«id»`, which
    resolves to core `id` -- clean and axiom-free -- while Lean declared the dirty `id.foo`, so
    `theorem «id».foo : False := evil` was stamped `Q.E.D.` A preamble decoy under the theorem's
    bare name won the same way.

    So the name is gone. Nothing is parsed, nothing is passed in, and there is no target to
    mis-aim: EVERY constant this module adds must have a clean closure. Strictly stronger than the
    old question (a dirty preamble helper now fails too), and it cannot be pointed at the wrong
    constant because it is not pointed at any. -/
def main (args : List String) : IO UInt32 := do
  match args with
  | [modName, nonce] =>
    initSearchPath (← findSysroot)
    let mod := modName.toName
    let env ← importModules #[{ module := mod }] {}
    match env.header.moduleNames.findIdx? (· == mod) with
    | none => IO.println s!"{nonce} MISSING {modName}"; return 1
    | some idx =>
      -- Constants THIS module declares. `getModuleIdxFor?` is `some` for everything after
      -- `importModules` (the target is itself an import), so compare against its own index.
      let ours := env.constants.fold (init := #[]) fun acc n _ =>
        if env.getModuleIdxFor? n == some idx then acc.push n else acc
      if ours.isEmpty then IO.println s!"{nonce} EMPTY {modName}"; return 1
      let mut all : NameSet := {}
      for c in ours do
        let (axs, _) ← (Lean.collectAxioms c : CoreM (Array Name)).toIO
            { fileName := "<axcheck>", fileMap := default } { env := env }
        for a in axs do all := all.insert a
      let names := all.toList.map toString
      IO.println s!"{nonce} AXIOMS {ours.size} [{", ".intercalate names}]"
      return 0
  | _ => IO.eprintln "usage: axcheck <module> <nonce>"; return 2
