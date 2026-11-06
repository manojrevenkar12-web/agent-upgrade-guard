# Held-out log

- **v1** (`v1.sha256`): wording written with dev, before any run. First run 2026-11-06; the result for
  the first version is in `v1/first_run.json`.
- **v1 findings**, which were fixed and checked on dev only:
  - the JSON field list took "kein" from ", kein weiterer Text" as a field, so both models failed
    every check and the obligation looked held;
  - "Duze die Mitarbeitenden niemals" was not read as formal address;
  - "haven't given" was not read as missing.

  These led to:
  - field lists limited to schema fields;
  - a negated form of "duzen" read as formal address;
  - the `suspect` state for checks that the current model also fails most of the time.
- **v2** (`v2.sha256`): wording written after the v1 run and pinned before any v1 fix was tried on it.
  First run 2026-11-06, after the fixes; the result for the current version is in `v2/first_run.json`.
- **After v2.** Forbidden-topic test messages use the owner's phrase ("legal advice on individual
  cases") instead of its keywords, and the dashboard was revised. The dev numbers in `reports/` include
  this change. The v2 numbers do not, and v2 was not run again.
- **Next.** Any change to `guard/spec.py` needs a v3 set, written before the change is tested on it.
