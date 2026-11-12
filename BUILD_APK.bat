@echo off
setlocal
title FLARE V2 - Build APK
cd /d "%~dp0"
set "LOG=%~dp0build_log.txt"
echo.
echo  ===== FLARE V2 : building the Android app =====
echo  First time takes 3-10 minutes and needs internet. Please wait...
echo.

rem --- always use Android Studio's own Java (older Java breaks Gradle 9) ---
set "AS_JBR="
if exist "C:\Program Files\Android\Android Studio\jbr\bin\java.exe" set "AS_JBR=C:\Program Files\Android\Android Studio\jbr"
if exist "%LOCALAPPDATA%\Programs\Android Studio\jbr\bin\java.exe" set "AS_JBR=%LOCALAPPDATA%\Programs\Android Studio\jbr"
if exist "%ProgramFiles%\Android\Android Studio Preview\jbr\bin\java.exe" if not defined AS_JBR set "AS_JBR=%ProgramFiles%\Android\Android Studio Preview\jbr"
if defined AS_JBR set "JAVA_HOME=%AS_JBR%"
if not defined JAVA_HOME (
  echo  Android Studio Java not found. Is Android Studio installed?
  echo  Android Studio Java not found > "%LOG%"
  pause
  exit /b 1
)
echo  Using Java: %JAVA_HOME%
echo  Using Java: %JAVA_HOME% > "%LOG%"
"%JAVA_HOME%\bin\java.exe" -version >> "%LOG%" 2>&1

cd 3_Android_App

rem --- stop old Gradle daemons + remove the corrupt cache lock (fixes "Unexpected lock protocol") ---
echo  Cleaning old Gradle locks...
call gradlew.bat --stop >> "%LOG%" 2>&1
if exist "%USERPROFILE%\.gradle\caches\journal-1\journal-1.lock" del /f /q "%USERPROFILE%\.gradle\caches\journal-1\journal-1.lock" >nul 2>&1
for /d %%D in ("%USERPROFILE%\.gradle\caches\*") do if exist "%%D\%%~nxD.lock" for %%F in ("%%D\%%~nxD.lock") do if %%~zF==0 del /f /q "%%F" >nul 2>&1

if exist "app\build\outputs\apk\debug\app-debug.apk" del /f /q "app\build\outputs\apk\debug\app-debug.apk" >nul 2>&1
echo  Building...
call gradlew.bat assembleDebug --console=plain --stacktrace >> "%LOG%" 2>&1
set "RESULT=%ERRORLEVEL%"

rem --- still a lock problem? build with a fresh private Gradle folder instead ---
if not "%RESULT%"=="0" (
  findstr /c:"lock protocol" /c:"lock file" "%LOG%" >nul && (
    echo  Gradle cache is damaged - retrying with a fresh cache, this takes longer...
    echo. >> "%LOG%"
    echo ===== RETRY WITH FRESH GRADLE_USER_HOME ===== >> "%LOG%"
    set "GRADLE_USER_HOME=%~dp0.gradle-home"
    call gradlew.bat assembleDebug --console=plain --stacktrace >> "%LOG%" 2>&1
  )
)
if exist "app\build\outputs\apk\debug\app-debug.apk" set "RESULT=0"
cd ..

if not "%RESULT%"=="0" goto failed
if not exist "3_Android_App\app\build\outputs\apk\debug\app-debug.apk" goto failed

copy /y "3_Android_App\app\build\outputs\apk\debug\app-debug.apk" "FLARE_V2.apk" >nul
echo BUILD OK >> "%LOG%"
echo.
echo  ===== DONE =====
echo  FLARE_V2.apk is now in this folder.
echo  Send it to your phone, tap it, allow "Install unknown apps".
echo.
pause
exit /b 0

:failed
echo BUILD FAILED >> "%LOG%"
echo.
echo  ===== BUILD FAILED =====
echo  Last lines of build_log.txt:
echo.
powershell -NoProfile -Command "Get-Content -Path '%LOG%' -Tail 30"
echo.
echo  Tell Claude "build failed" - it can read build_log.txt itself.
pause
exit /b 1
