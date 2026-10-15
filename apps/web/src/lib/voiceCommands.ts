/** 只匹配明确结束本次语音的整句，避免把“结束会议”等普通话语误当退出。 */
export function isVoiceStopCommand(text: string): boolean {
  const clean = text.toLowerCase().replace(/[\s，,。.!！?？、]/gu, "");
  return /^(?:ok|okay|好的|好)?(?:结束|结束语音|停止监听|退出语音)$/u.test(clean);
}
