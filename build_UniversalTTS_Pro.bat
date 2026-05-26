@echo off
REM ════════════════════════════════════════════════════════════════════
REM  build_UniversalTTS_Pro.bat
REM  Futtasd a projekt gyökérmappájából!
REM  Automatikus PyInstaller ellenőrzéssel és Python modul hívással
REM ════════════════════════════════════════════════════════════════════

echo.
echo  === UniversalTTS_Pro BUILD INDUL ===
echo.

REM PyInstaller ellenőrzés a Python modulon keresztül
python -m PyInstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] PyInstaller modul nem talalhato. Telepites...
    python -m pip install pyinstaller
    
    :: Újra ellenőrizzük modulként
    python -m PyInstaller --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [HIBA] A PyInstaller modulkent sem indithato el!
        echo Ellenorizd a Python telepitesedet.
        pause
        exit /b 1
    )
)

echo [OK] PyInstaller modul keszen all.
echo.

REM Build futtatása explicit módon a Python modul meghívásával
python -m PyInstaller UniversalTTS_Pro.spec --noconfirm --clean

if %errorlevel% neq 0 (
    echo.
    echo [HIBA] Build sikertelen!
    pause
    exit /b 1
)

REM ── models/ mappa másolása az exe mellé (nem _internal-ba!) ──
if exist "models" (
    echo.
    echo  Modellek masolasa: dist\UniversalTTS_Pro\models\
    if exist "dist\UniversalTTS_Pro\models" (
        rmdir /s /q "dist\UniversalTTS_Pro\models"
    )
    xcopy /E /I /Q "models" "dist\UniversalTTS_Pro\models"
    echo  [OK] models/ atmasolva
) else (
    echo  [FIGYELEM] models/ mappa nem talalhato - kezileg masold at!
)

echo.
echo  === BUILD SIKERESEN BEFEJEZODOTT ===
echo  Az elerheto program itt talalhato: dist\UniversalTTS_Pro\
echo.
pause