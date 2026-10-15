#Requires -Version 7.0
param([string]$Keyword = '嘿宇', [switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$engine = $null
try {
    Add-Type -AssemblyName System.Speech
    $info = [System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers() |
        Where-Object { $_.Culture.Name -eq 'zh-CN' } | Select-Object -First 1
    if (-not $info) { throw '未安装 Windows 中文语音识别引擎。' }
    $engine = [System.Speech.Recognition.SpeechRecognitionEngine]::new($info)
    $grammar = [System.Speech.Recognition.GrammarBuilder]::new()
    $grammar.Culture = $info.Culture
    $grammar.Append($Keyword)
    $engine.LoadGrammar([System.Speech.Recognition.Grammar]::new($grammar))
    if ($CheckOnly) {
        [Console]::WriteLine('{"type":"ready"}')
        exit 0
    }
    # stdin 是唯一采集流输出的 PCM；该进程不自行打开麦克风。
    $format = [System.Speech.AudioFormat.SpeechAudioFormatInfo]::new(
        16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,
        [System.Speech.AudioFormat.AudioChannel]::Mono)
    Add-Type -Path (Join-Path $PSScriptRoot 'PcmPipeStream.cs')
    $inputStream = [YuPcmPipeStream]::new([Console]::OpenStandardInput())
    [Console]::WriteLine('{"type":"ready"}')
    [Console]::Out.Flush()
    while ($true) {
        $engine.SetInputToAudioStream($inputStream, $format)
        $result = $engine.Recognize([TimeSpan]::FromSeconds(30))
        if ($result) {
            $eventData = @{type='wake'; text=$result.Text; confidence=$result.Confidence}
            [Console]::WriteLine(($eventData | ConvertTo-Json -Compress))
            [Console]::Out.Flush()
        }
    }
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    [Console]::WriteLine((@{type='error';message=$_.Exception.Message} | ConvertTo-Json -Compress))
    exit 1
} finally {
    if ($engine) { $engine.Dispose() }
}
