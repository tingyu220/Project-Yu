# 请使用 PowerShell 7 运行；.env 仅保存在本机且已加入 Git 忽略。
#Requires -Version 7.0
$ErrorActionPreference = 'Stop'
$previousKey = $env:DASHSCOPE_API_KEY
$previousRegion = $env:YU_VOICE_REGION
$previousOpen = $env:YU_ALLOW_LOCAL_OPEN
$previousMedia = $env:YU_ALLOW_MEDIA_CONTROL
$previousPort = $env:YU_API_PORT
$previousUtf8 = $env:PYTHONUTF8
$envPath = Join-Path $PSScriptRoot '.env'
Push-Location $PSScriptRoot
try {
    Write-Host ('Yu 语音启动检查 | PowerShell ' + $PSVersionTable.PSVersion)
    $pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $pythonPath)) {
        throw '项目缺少 .venv Python 环境，请先安装项目依赖。'
    }
    & $pythonPath -c 'import uvicorn; import websockets.asyncio.client; import yu.api.app'
    if ($LASTEXITCODE -ne 0) { throw 'Python/API 依赖检查失败，请查看上方错误。' }
    $listener = Get-NetTCPConnection -LocalPort 8792 -State Listen -ErrorAction SilentlyContinue
    if ($listener) { throw '8792 端口已被占用。若 Yu 已启动，请访问 http://127.0.0.1:8792；否则先关闭占用程序。' }
    if (Test-Path -LiteralPath $envPath) {
        foreach ($line in Get-Content -LiteralPath $envPath) {
            if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$' -and $Matches[1] -eq 'DASHSCOPE_API_KEY') {
                $savedKey = $Matches[2].Trim().Trim('"').Trim("'")
                if ($savedKey) { $env:DASHSCOPE_API_KEY = $savedKey }
            }
        }
    }
    if (-not $env:DASHSCOPE_API_KEY) {
        $env:DASHSCOPE_API_KEY = Read-Host '首次运行请输入北京地域百炼 API Key（将保存到本机 .env，隐藏输入）' -MaskInput
        if (-not [string]::IsNullOrWhiteSpace($env:DASHSCOPE_API_KEY)) {
            # 只追加缺失密钥，保留现有 .env 中的其他配置。
            ("`nDASHSCOPE_API_KEY=$($env:DASHSCOPE_API_KEY)") | Add-Content -LiteralPath $envPath -Encoding utf8NoBOM
            Write-Host 'Key 已保存到本机 .env，后续启动无需重复输入。'
        }
    }
    if ([string]::IsNullOrWhiteSpace($env:DASHSCOPE_API_KEY)) { throw '未提供密钥，启动取消。' }
    $env:YU_VOICE_REGION = 'cn-beijing'
    $env:YU_ALLOW_LOCAL_OPEN = '1'
    $env:YU_ALLOW_MEDIA_CONTROL = '1'
    $env:YU_API_PORT = '8792'
    $env:PYTHONUTF8 = '1'
    Write-Host '启动后自动本地待唤醒；说“嘿，宇”，听到提示音后直接说指令，不用打开网页或点按钮。'
    Write-Host '待唤醒会使用麦克风，但不上传音频；唤醒后的对话使用阿里云北京识别并产生费用。'
    Write-Host '本次允许本地打开及QQ音乐控制；说“结束”回到待唤醒，Ctrl+C 完全停止。'
    & $pythonPath -m yu.voice.wake.launcher
    if ($LASTEXITCODE -ne 0) { throw ('Yu 服务退出，退出码：' + $LASTEXITCODE + '。请查看上方错误。') }
} catch {
    Write-Host ('启动未完成：' + $_.Exception.Message) -ForegroundColor Red
    Write-Host '请使用 start-voice.cmd 双击启动，窗口会保留错误信息。'
    throw
} finally {
    $env:DASHSCOPE_API_KEY = $previousKey
    $env:YU_VOICE_REGION = $previousRegion
    $env:YU_ALLOW_LOCAL_OPEN = $previousOpen
    $env:YU_ALLOW_MEDIA_CONTROL = $previousMedia
    $env:YU_API_PORT = $previousPort
    $env:PYTHONUTF8 = $previousUtf8
    Pop-Location
}
