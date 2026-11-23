import React from 'react';
import { StyleSheet, View } from 'react-native';
import Svg, { Circle, Defs, Pattern, Rect } from 'react-native-svg';

import { useAppTheme } from '../context/ThemeContext';

export function DotPatternBackground() {
  const { theme } = useAppTheme();
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      <Svg width="100%" height="100%">
        <Defs>
          <Pattern id="dotGrid" x="0" y="0" width="16" height="16" patternUnits="userSpaceOnUse">
            <Circle cx="3" cy="3" r="1.2" fill={theme.cardDot} />
          </Pattern>
        </Defs>
        <Rect width="100%" height="100%" fill="url(#dotGrid)" />
      </Svg>
    </View>
  );
}
