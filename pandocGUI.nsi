Unicode True
RequestExecutionLevel user
SetCompressor /SOLID lzma

!include "MUI2.nsh"

!define PRODUCT_NAME "pandocGUI"
!define PRODUCT_VERSION "0.1.0"
!define PRODUCT_PUBLISHER "pandocGUI"
!define PRODUCT_EXE "pandocGUI.exe"
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\pandocGUI"

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "output\pandocGUI-${PRODUCT_VERSION}-win-x64-setup.exe"
InstallDir "$LOCALAPPDATA\Programs\pandocGUI"
InstallDirRegKey HKCU "Software\pandocGUI" "InstallDir"
Icon "..\Pandoc-GUI.ico"
UninstallIcon "..\Pandoc-GUI.ico"

!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\${PRODUCT_EXE}"
!define MUI_FINISHPAGE_LINK "pandocGUI 不包含 Pandoc，点击查看 Pandoc 安装说明"
!define MUI_FINISHPAGE_LINK_LOCATION "https://pandoc.org/installing.html"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "SimpChinese"

Section "pandocGUI（必需）" SEC_MAIN
  SectionIn RO
  SetOutPath "$INSTDIR"
  File /r "..\dist\pandocGUI\*.*"
  WriteUninstaller "$INSTDIR\uninstall.exe"
  CreateDirectory "$SMPROGRAMS\pandocGUI"
  CreateShortcut "$SMPROGRAMS\pandocGUI\pandocGUI.lnk" "$INSTDIR\${PRODUCT_EXE}"
  CreateShortcut "$SMPROGRAMS\pandocGUI\卸载 pandocGUI.lnk" "$INSTDIR\uninstall.exe"
  WriteRegStr HKCU "Software\pandocGUI" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\${PRODUCT_EXE}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "UninstallString" '$\"$INSTDIR\uninstall.exe$\"'
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoRepair" 1
SectionEnd

Section /o "桌面快捷方式" SEC_DESKTOP
  CreateShortcut "$DESKTOP\pandocGUI.lnk" "$INSTDIR\${PRODUCT_EXE}"
SectionEnd

LangString DESC_SEC_MAIN ${LANG_SIMPCHINESE} "安装 pandocGUI 应用程序（不包含 pandoc.exe）。"
LangString DESC_SEC_DESKTOP ${LANG_SIMPCHINESE} "在当前用户桌面创建快捷方式。"

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MAIN} $(DESC_SEC_MAIN)
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_DESKTOP} $(DESC_SEC_DESKTOP)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Section "Uninstall"
  Delete "$DESKTOP\pandocGUI.lnk"
  RMDir /r "$SMPROGRAMS\pandocGUI"
  DeleteRegKey HKCU "${UNINSTALL_KEY}"
  DeleteRegKey HKCU "Software\pandocGUI"
  RMDir /r "$INSTDIR"
SectionEnd
