#Requires -Version 7.0
param([string]$Text = '嘿宇')
# 集成测试生成内存 PCM，不播放、不录音、不写文件、不联网。
Add-Type -AssemblyName System.Speech
$speaker = [System.Speech.Synthesis.SpeechSynthesizer]::new()
$memory = [System.IO.MemoryStream]::new()
try {
    $voice = $speaker.GetInstalledVoices() | Where-Object {
        $_.Enabled -and $_.VoiceInfo.Culture.Name -eq 'zh-CN'
    } | Select-Object -First 1
    if (-not $voice) { exit 2 }
    $speaker.SelectVoice($voice.VoiceInfo.Name)
    $format = [System.Speech.AudioFormat.SpeechAudioFormatInfo]::new(
        16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,
        [System.Speech.AudioFormat.AudioChannel]::Mono)
    $speaker.SetOutputToAudioStream($memory, $format)
    $speaker.Speak($Text)
    [Console]::WriteLine([Convert]::ToBase64String($memory.ToArray()))
} finally {
    $speaker.Dispose()
    $memory.Dispose()
}
