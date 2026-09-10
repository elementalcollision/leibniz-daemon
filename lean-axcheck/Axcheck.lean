import Lean
open Lean Core

def main (args : List String) : IO UInt32 := do
  match args with
  | [modName, declName, nonce] =>
    initSearchPath (← findSysroot)
    let env ← importModules #[{ module := modName.toName }] {}
    let decl := declName.toName
    if (env.find? decl).isNone then
      IO.println s!"{nonce} MISSING {declName}"
      return 1
    let (axs, _) ← (Lean.collectAxioms decl : CoreM (Array Name)).toIO
        { fileName := "<axcheck>", fileMap := default } { env := env }
    IO.println s!"{nonce} AXIOMS {declName} [{", ".intercalate (axs.toList.map toString)}]"
    return 0
  | _ => IO.eprintln "usage: axcheck <module> <decl> <nonce>"; return 2
