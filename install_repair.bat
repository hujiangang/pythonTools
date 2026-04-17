@echo off
echo 正在安装依赖...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo ==============================
echo 依赖安装完成！
echo ==============================
pause