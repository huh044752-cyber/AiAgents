Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  AI 飞行仿真 Agent - 启动 Web 控制台" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot

if (Test-Path "venv\Scripts\Activate.ps1") {
    & "venv\Scripts\Activate.ps1"
    Write-Host "[OK] 虚拟环境已激活" -ForegroundColor Green
} else {
    Write-Host "[WARN] 未找到虚拟环境，使用系统 Python" -ForegroundColor Yellow
}

Write-Host "[INFO] 启动 Streamlit..." -ForegroundColor Yellow
Write-Host "[INFO] 浏览器将自动打开 http://localhost:8501" -ForegroundColor Yellow
Write-Host ""

streamlit run ui/app.py --server.port 8501 --server.headless false --theme.base dark
