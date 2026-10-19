from pathlib import Path
p=Path('docs/handoffs/MAINTENANCE_PONDER_2.9.4_HANDOFF.txt');s=p.read_text();s=s.replace('Release verification: pending final build/install checks.', '''Release verification completed
360 tests passed in 158.31 seconds: .qa/opening-294/release.xml.
A live packaged test exposed animation repeatedly restarting a cold tutorial
render. Fixed the build key to finish the current sample and added the advancing-
animation regression. Rebuilt both artifacts after the fix.

Root BlocFantome.exe and Code/build/installer/BlocFantome_Setup_2.9.4.exe built
successfully. Archive check: 938 source/visual files byte-for-byte, new opening
module, Tk dialogs and native acceleration. Source/root/installer metadata 2.9.4.
Installed EXE matches root SHA256:
FDECB520F92C71658DC054C7F6929BF73F173318B26DD64455878E568D835F14

Upgraded C:\\Users\\hunkb\\AppData\\Local\\Programs\\Bloc Fantome (accented folder).
Actual Start Menu Bloc Fantome shortcut launched that installed 2.9.4 EXE.
Target, icon and working directory verified for app/uninstaller shortcuts:
.qa/consistency-start-menu-294.json.
Live UI: fitted full-aspect swamp painting/title strip; opening scene; ghost
placement, grouped reveal and clickable Q/E; return to visible tutorial; root
Zoom then Next resets framing. Installed opening and tutorial return checked.
Keyboard event handling passes integration tests; this desktop helper's synthetic
key events did not visibly act, so live keyboard behavior is not claimed here.

50 existing save/settings files unchanged after installation and live QA.
Installed font, music and painting hashes match source:
.qa/opening-294/preservation-and-assets.json.
All exact-path root/installed QA processes closed; zero remain:
.qa/opening-294/packaged-live-checks.json.
Build/install logs: .qa/opening-294/build-final.log, installer-final.log, install.log.''');p.write_text(s)
p=Path('docs/handoffs/MAINTENANCE_2.9.3_CHECKPOINT.txt')
if p.exists():
 s=p.read_text(encoding='utf-8')
 p.write_text('SUPERSEDED: completed 2.9.4 release, installation and Start Menu verification\nare recorded in MAINTENANCE_PONDER_2.9.4_HANDOFF.txt. Historical checkpoint below.\n\n'+s,encoding='utf-8')
