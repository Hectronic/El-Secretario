# Tasks: Native Packaging and Auto-Updating Installers

Status: Draft
Last updated: 2026-09-15

- [ ] T001 Define and build Debian `.deb` package directory structure and postinst control scripts.
- [ ] T002 Implement `/usr/bin/el-secretario` launcher with user-space repo self-clone & auto-update bootstrapper.
- [ ] T003 Create Windows Inno Setup `.iss` installer compiler script targeting `{localappdata}` without administrative restrictions.
- [ ] T004 Implement Windows post-install silent bootstrapper call to initialize git cloning and pip dependencies.
- [ ] T005 Construct macOS `.app` shell bundle and shell launcher with user-space application support folder isolation.
- [ ] T006 Compile macOS `.app` bundle into a clean drag-and-drop `.dmg` installer.
- [ ] T007 Build validation suite to test "Enable Auto-Updates" settings toggling across all three packaged environments.
