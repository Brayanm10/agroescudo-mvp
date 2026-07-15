export const passwordRequirements = [
  "Minimo 8 caracteres",
  "Al menos una letra",
  "Al menos un numero"
];

export function validatePasswordStrength(password: string) {
  if (password.length < 8) return "La contrasena debe tener minimo 8 caracteres.";
  if (!/[A-Za-z]/.test(password)) return "La contrasena debe incluir al menos una letra.";
  if (!/[0-9]/.test(password)) return "La contrasena debe incluir al menos un numero.";
  return null;
}
