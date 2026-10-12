import type { ConstellationFieldProps } from '../../components/backgrounds/ConstellationFieldBackground';
import ConstellationFieldBackground from '../../components/backgrounds/ConstellationFieldBackground';

export { ConstellationFieldBackground, type ConstellationFieldProps };

export function ConstellationField(props: ConstellationFieldProps) {
  return <ConstellationFieldBackground {...props} />;
}

export default ConstellationField;
