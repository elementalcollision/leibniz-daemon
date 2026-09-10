import Lean
open Lean Core

/-- Resolve `decl` in `env`: exact match first, else the UNIQUE module-local constant whose last
    name component is `decl`. The second case exists because an ADR 0062 preamble may open a
    namespace, so the declaration Lean actually stores is `Ns.decl`. Restricting the search to
    module-local constants (`getModuleIdxFor?` is none for those) keeps it unambiguous -- Mathlib
    has thousands of matching suffixes, this module has a handful of declarations. Ambiguous or
    absent resolves to none, and the caller treats that as a refusal. -/
def resolve (env : Environment) (mod : Name) (decl : Name) : Option Name :=
  if (env.find? decl).isSome then some decl
  else
    -- Constants declared by OUR module. Note `getModuleIdxFor?` is `some` for every constant
    -- here: after `importModules` the target module is itself an import, so a "module-local"
    -- test on `isNone` matches nothing. Compare against the target module's own index instead.
    let idx? := env.header.moduleNames.findIdx? (· == mod)
    match idx? with
    | none => none
    | some idx =>
      let cands := env.constants.fold (init := #[]) fun acc n _ =>
        if env.getModuleIdxFor? n == some idx && !n.isInternal
           && n.components.getLast? == decl.components.getLast?
        then acc.push n else acc
      if cands.size == 1 then some cands[0]! else none

/-- Report the axiom closure of `decl` in module `mod`, tagged with a caller-supplied nonce.

    ADR 0097. Compiled into the image BEFORE any proposer text exists, so `elab_rules` /
    `macro_rules` cannot change what it does: it elaborates no proposer syntax and reads
    `ConstantInfo` data rather than a printed message. Round 6 removed the `def <probe> := @<name>`
    alias this used to be asked about -- that was surface syntax a smuggled
    `macro_rules | `(@$_:ident) => ...` could rewrite, so the question was aimed at the wrong
    constant while the answer stayed honest. The name now arrives as ARGV, which no macro reaches. -/
def main (args : List String) : IO UInt32 := do
  match args with
  | [modName, declName, nonce] =>
    initSearchPath (← findSysroot)
    let env ← importModules #[{ module := modName.toName }] {}
    match resolve env modName.toName declName.toName with
    | none => IO.println s!"{nonce} MISSING {declName}"; return 1
    | some decl =>
      let (axs, _) ← (Lean.collectAxioms decl : CoreM (Array Name)).toIO
          { fileName := "<axcheck>", fileMap := default } { env := env }
      IO.println s!"{nonce} AXIOMS {declName} [{", ".intercalate (axs.toList.map toString)}]"
      return 0
  | _ => IO.eprintln "usage: axcheck <module> <decl> <nonce>"; return 2
