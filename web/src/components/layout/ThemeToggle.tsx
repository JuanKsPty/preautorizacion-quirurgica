import { MoonIcon, SunIcon } from 'lucide-react';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const esOscuro = resolvedTheme === 'dark';

  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label={esOscuro ? 'Activar tema claro' : 'Activar tema oscuro'}
      onClick={() => setTheme(esOscuro ? 'light' : 'dark')}
    >
      {esOscuro ? <SunIcon /> : <MoonIcon />}
    </Button>
  );
}
