@echo off
REM Build ISMS Demo for Windows using PyInstaller
REM Run this on Windows with Python 3.12+ installed.
REM On Linux/macOS, use: docker build -f Dockerfile.build .

echo === Installing dependencies ===
pip install -r requirements.txt
pip install pyinstaller

echo === Pre-compiling translations ===
pybabel compile -d app/translations

echo === Finding reportlab barcode path ===
for /f "delims=" %%i in ('python -c "import os, reportlab.graphics.barcode; print(os.path.dirname(reportlab.graphics.barcode.__file__))"') do set BARCODE_DIR=%%i
echo Barcode dir: %BARCODE_DIR%

echo === Building Windows executable ===
pyinstaller --name=ISMS-Demo ^
  --onedir ^
  --windowed ^
  --noconfirm ^
  --add-data "app/templates;app/templates" ^
  --add-data "app/static;app/static" ^
  --add-data "app/translations;app/translations" ^
  --add-data "seed_data;seed_data" ^
  --hidden-import "waitress" ^
  --hidden-import "flask" ^
  --hidden-import "flask_sqlalchemy" ^
  --hidden-import "flask_login" ^
  --hidden-import "flask_wtf" ^
  --hidden-import "flask_mail" ^
  --hidden-import "flask_migrate" ^
  --hidden-import "flask_babel" ^
  --hidden-import "flask_limiter" ^
  --hidden-import "flask_talisman" ^
  --hidden-import "flask_session" ^
  --hidden-import "qrcode" ^
  --hidden-import "pyotp" ^
  --hidden-import "ldap3" ^
  --hidden-import "openai" ^
  --hidden-import "dotenv" ^
  --hidden-import "PIL" ^
  --hidden-import "PIL._tkinter_finder" ^
  --hidden-import "reportlab" ^
  --hidden-import "reportlab.graphics.barcode" ^
  --hidden-import "reportlab.graphics.barcode.code128" ^
  --hidden-import "reportlab.graphics.barcode.code39" ^
  --hidden-import "reportlab.graphics.barcode.code93" ^
  --hidden-import "reportlab.graphics.barcode.common" ^
  --hidden-import "reportlab.graphics.barcode.eanbc" ^
  --hidden-import "reportlab.graphics.barcode.qr" ^
  --hidden-import "reportlab.graphics.barcode.widgets" ^
  --hidden-import "reportlab.graphics.barcode.usps" ^
  --hidden-import "reportlab.graphics.barcode.usps4s" ^
  --hidden-import "reportlab.graphics.barcode.lto" ^
  --hidden-import "reportlab.graphics.barcode.fourstate" ^
  --collect-all "reportlab.graphics.barcode" ^
  --add-data "%BARCODE_DIR%;reportlab\graphics\barcode" ^
  --hidden-import "xhtml2pdf" ^
  --hidden-import "bleach" ^
  --hidden-import "markdown" ^
  --hidden-import "openpyxl" ^
  --hidden-import "docx" ^
  --hidden-import "apscheduler" ^
  --hidden-import "email_validator" ^
  --hidden-import "redis" ^
  --collect-all "flask" ^
  --collect-all "app" ^
  demo.py

echo === Build complete! ===
echo Output: dist\ISMS-Demo\ISMS-Demo.exe
