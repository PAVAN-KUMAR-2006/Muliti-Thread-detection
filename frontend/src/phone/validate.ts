/** First-line check so obvious mistakes get instant feedback. The server validates again and is the authority. */
export function validatePhoneInput(raw: string, region: string): string {
  const v = raw.trim();
  if (!v) return "Enter a phone number.";
  if (v.length > 32 || !/^[0-9+()\-.\s]+$/.test(v)) return "A phone number can contain only digits, spaces and the characters + ( ) - .";
  const digits = v.replace(/\D/g, "");
  if (digits.length < 4) return "That is too short to be a phone number.";
  if (digits.length > 15) return "That is too long to be a phone number.";
  if (!v.startsWith("+") && !region) return "Choose a country, or start the number with + and its country code.";
  return "";
}
