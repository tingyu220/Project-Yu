#Requires -Version 7.0
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
$speaker = $null
try {
    Add-Type -AssemblyName System.Speech
    $speaker = [System.Speech.Synthesis.SpeechSynthesizer]::new()
    $voice = $speaker.GetInstalledVoices() | Where-Object {
        $_.Enabled -and $_.VoiceInfo.Culture.Name -eq 'zh-CN'
    } | Select-Object -First 1
    if (-not $voice) { throw '未安装中文本地音色。' }
    $speaker.SelectVoice($voice.VoiceInfo.Name)
    $speaker.SetOutputToDefaultAudioDevice()
    $text = [Console]::In.ReadToEnd()
    if ($text.Length -gt 0) { $speaker.Speak($text) }
} catch {
    exit 1
} finally {
    if ($speaker) { $speaker.Dispose() }
}
