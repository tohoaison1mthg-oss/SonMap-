# SonMap+ versioning

The user requires a new version number for every user-visible upgrade, including
work continued on another computer. Read VERSION, CHANGELOG.md and current Git
branches/tags before releasing. Increment the minor component once per upgrade
(e.g. 10.3 -> 10.4 -> 10.5); do not reuse informal dev-v1/v2 labels as app versions.
VERSION is the source of truth for the application title, installer, shortcut
and package filename. Record each release in CHANGELOG.md. Do not lower a newer
installed version or discard work made on another branch/computer.

Run the relevant Python tests and package integrity checks before distribution.
Distinguish cloud tests from Windows/V8i/Jet validation. Preserve user DGN/MDB,
settings, runtime, assets and data during updates. Keep source on the existing
GitHub development branch unless the user asks to merge/publish it elsewhere.

Keep both old and new releases: never overwrite a versioned package or Git tag.
Create immutable tags for release commits and retain old source archives. Push
release commits/tags to the existing repository so another computer can resume.
The laptop updater must back up replaced program files, preserve private data,
and offer program rollback while also saving the version being rolled back.
