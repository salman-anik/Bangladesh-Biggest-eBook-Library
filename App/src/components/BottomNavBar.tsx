import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Animated,
  Dimensions,
  type LayoutChangeEvent,
  StyleSheet,
  TouchableOpacity,
  View,
} from 'react-native';
import Svg, {
  Circle,
  Defs,
  Line,
  LinearGradient,
  Path,
  Rect,
  Stop,
} from 'react-native-svg';

import { useAppTheme } from '../context/ThemeContext';
import type { TabKey, ThemePresetKey } from '../types';

interface Props {
  activeTab: TabKey;
  onSelectTab: (tab: TabKey) => void;
  bottomInset?: number;
}

interface TabIconProps {
  color: string;
  active: boolean;
}

const CIRCLE_SIZE = 58;
const TOP_OVERHANG = 18;
const BAR_BASE_HEIGHT = 62;
const NOTCH_DEPTH = 41;

const ORB_GRADIENTS: Record<ThemePresetKey, [string, string]> = {
  espresso: ['#E0A084', '#7E4431'],
  matcha: ['#8EC9A0', '#2E5E42'],
  midnight: ['#8AAAE8', '#2C4278'],
  sepia: ['#E5AF67', '#80511C'],
  rosewood: ['#E85D8A', '#7A1F4B'],
};

function HomeIcon({ color, active }: TabIconProps) {
  if (active) {
    return (
      <Svg width={22} height={22} viewBox="0 0 24 24" fill="#FFFFFF">
        <Path d="M11.36 2.74a1 1 0 0 1 1.28 0l8.5 7.08A1 1 0 0 1 21.5 10.6V20a1.5 1.5 0 0 1-1.5 1.5h-5.25a.75.75 0 0 1-.75-.75V15a1 1 0 0 0-1-1h-2a1 1 0 0 0-1 1v5.75a.75.75 0 0 1-.75.75H4A1.5 1.5 0 0 1 2.5 20v-9.4a1 1 0 0 1 .36-.78l8.5-7.08z" />
      </Svg>
    );
  }
  return (
    <Svg
      width={22}
      height={22}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={1.85}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <Path d="M3 10.5L12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1v-9.5z" />
    </Svg>
  );
}

function LibraryNavIcon({ color, active }: TabIconProps) {
  if (active) {
    return (
      <Svg width={22} height={22} viewBox="0 0 24 24" fill="#FFFFFF">
        <Path d="M18.5 2.5h-13A1.5 1.5 0 0 0 4 4v17.2a.8.8 0 0 0 1.26.65L12 17.2l6.74 4.65A.8.8 0 0 0 20 21.2V4a1.5 1.5 0 0 0-1.5-1.5z" />
      </Svg>
    );
  }
  return (
    <Svg
      width={22}
      height={22}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={1.85}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <Path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
    </Svg>
  );
}

function ExploreGridIcon({ color, active }: TabIconProps) {
  if (active) {
    return (
      <Svg width={22} height={22} viewBox="0 0 24 24" fill="#FFFFFF">
        <Rect x="3" y="3" width="8" height="8" rx="2.2" />
        <Rect x="13" y="3" width="8" height="8" rx="2.2" />
        <Rect x="3" y="13" width="8" height="8" rx="2.2" />
        <Rect x="13" y="13" width="8" height="8" rx="2.2" />
      </Svg>
    );
  }
  return (
    <Svg
      width={22}
      height={22}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={1.85}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <Rect x="3.5" y="3.5" width="7" height="7" rx="1.8" />
      <Rect x="13.5" y="3.5" width="7" height="7" rx="1.8" />
      <Rect x="3.5" y="13.5" width="7" height="7" rx="1.8" />
      <Rect x="13.5" y="13.5" width="7" height="7" rx="1.8" />
    </Svg>
  );
}

function SearchNavIcon({ color, active }: TabIconProps) {
  if (active) {
    return (
      <Svg width={22} height={22} viewBox="0 0 24 24" fill="none">
        <Circle cx="10.5" cy="10.5" r="7" fill="#FFFFFF" fillOpacity={0.28} stroke="#FFFFFF" strokeWidth={2.5} />
        <Line x1="20.5" y1="20.5" x2="15.8" y2="15.8" stroke="#FFFFFF" strokeWidth={2.7} strokeLinecap="round" />
      </Svg>
    );
  }
  return (
    <Svg
      width={22}
      height={22}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <Circle cx="10.5" cy="10.5" r="7" />
      <Line x1="21" y1="21" x2="15.6" y2="15.6" />
    </Svg>
  );
}

function SettingsNavIcon({ color, active }: TabIconProps) {
  if (active) {
    return (
      <Svg width={22} height={22} viewBox="0 0 24 24" fill="none">
        <Path
          d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"
          fill="#FFFFFF"
        />
        <Circle cx="12" cy="12" r="3.2" fill="#000000" fillOpacity={0.28} />
      </Svg>
    );
  }
  return (
    <Svg
      width={22}
      height={22}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={1.85}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <Circle cx="12" cy="12" r="3" />
      <Path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </Svg>
  );
}

const TABS: {
  key: TabKey;
  label: string;
  Icon: React.ComponentType<TabIconProps>;
}[] = [
  { key: 'home', label: 'Home', Icon: HomeIcon },
  { key: 'library', label: 'Shelf', Icon: LibraryNavIcon },
  { key: 'explore', label: 'Explore', Icon: ExploreGridIcon },
  { key: 'search', label: 'Search', Icon: SearchNavIcon },
  { key: 'more', label: 'Settings', Icon: SettingsNavIcon },
];

function buildDockedNotchPath(width: number, totalHeight: number, cx: number): string {
  const w = Math.max(width, 240);
  const h = totalHeight;
  const tabW = w / TABS.length;
  const halfW = Math.min(43, tabW * 0.49);
  const d = NOTCH_DEPTH;

  const leftS = Math.max(0, cx - halfW);
  const rightS = Math.min(w, cx + halfW);
  const lSpan = cx - leftS;
  const rSpan = rightS - cx;

  return [
    'M 0 0',
    leftS > 0.5 ? `L ${leftS.toFixed(2)} 0` : '',
    `C ${(leftS + lSpan * 0.44).toFixed(2)} 0 ${(cx - lSpan * 0.62).toFixed(2)} ${d} ${cx.toFixed(2)} ${d}`,
    `C ${(cx + rSpan * 0.62).toFixed(2)} ${d} ${(rightS - rSpan * 0.44).toFixed(2)} 0 ${rightS.toFixed(2)} 0`,
    rightS < w - 0.5 ? `L ${w.toFixed(2)} 0` : '',
    `L ${w} ${h}`,
    `L 0 ${h}`,
    'Z',
  ]
    .filter(Boolean)
    .join(' ');
}

export const BottomNavBar = React.memo(function BottomNavBar({
  activeTab,
  onSelectTab,
  bottomInset = 8,
}: Props) {
  const { theme, preset } = useAppTheme();
  const [barWidth, setBarWidth] = useState(() => Math.max(Dimensions.get('window').width, 320));

  const activeIdx = Math.max(
    0,
    TABS.findIndex((t) => t.key === activeTab)
  );
  const tabWidth = barWidth / TABS.length;
  const targetCx = tabWidth * (activeIdx + 0.5);

  const animX = useRef(new Animated.Value(targetCx)).current;
  const [notchCx, setNotchCx] = useState(targetCx);
  const prevWidthRef = useRef(barWidth);

  useEffect(() => {
    const id = animX.addListener(({ value }) => {
      setNotchCx(value);
    });
    return () => {
      animX.removeListener(id);
    };
  }, [animX]);

  useEffect(() => {
    if (prevWidthRef.current !== barWidth) {
      prevWidthRef.current = barWidth;
      animX.setValue(targetCx);
      setNotchCx(targetCx);
      return;
    }
    Animated.spring(animX, {
      toValue: targetCx,
      damping: 18,
      stiffness: 170,
      mass: 0.75,
      useNativeDriver: false,
    }).start();
  }, [targetCx, barWidth, animX]);

  const insetH = Math.max(bottomInset, 6);
  const barTotalH = BAR_BASE_HEIGHT + insetH;

  const notchPath = useMemo(
    () => buildDockedNotchPath(barWidth, barTotalH, notchCx),
    [barWidth, barTotalH, notchCx]
  );

  const handleLayout = (e: LayoutChangeEvent) => {
    const nextW = Math.round(e.nativeEvent.layout.width);
    if (nextW > 120 && nextW !== barWidth) {
      setBarWidth(nextW);
    }
  };

  const [gradStart, gradEnd] = ORB_GRADIENTS[preset] || ORB_GRADIENTS.espresso;
  const ActiveIcon = TABS[activeIdx]?.Icon || HomeIcon;
  const orbTranslateX = Animated.subtract(animX, CIRCLE_SIZE / 2);

  return (
    <View
      style={[styles.outerWrap, { height: TOP_OVERHANG + barTotalH }]}
      onLayout={handleLayout}
      pointerEvents="box-none"
    >
      {/* Full-width docked curved bar */}
      <View style={[styles.dockSvgWrap, { top: TOP_OVERHANG, height: barTotalH }]} pointerEvents="none">
        <Svg width={barWidth} height={barTotalH}>
          <Path d={notchPath} fill={theme.surface} />
        </Svg>
      </View>

      {/* Glossy Gradient Floating Active Orb centered in semicircular notch */}
      <Animated.View
        style={[
          styles.orbOuter,
          {
            transform: [{ translateX: orbTranslateX }],
          },
        ]}
      >
        <TouchableOpacity
          style={styles.orbTouch}
          onPress={() => onSelectTab(TABS[activeIdx].key)}
          activeOpacity={0.92}
          accessibilityRole="tab"
          accessibilityState={{ selected: true }}
          accessibilityLabel={TABS[activeIdx].label}
        >
          <Svg width={CIRCLE_SIZE} height={CIRCLE_SIZE} style={StyleSheet.absoluteFill}>
            <Defs>
              <LinearGradient id="navOrbGrad" x1="12%" y1="8%" x2="88%" y2="92%">
                <Stop offset="0%" stopColor={gradStart} />
                <Stop offset="100%" stopColor={gradEnd} />
              </LinearGradient>
            </Defs>
            <Circle
              cx={CIRCLE_SIZE / 2}
              cy={CIRCLE_SIZE / 2}
              r={CIRCLE_SIZE / 2}
              fill="url(#navOrbGrad)"
            />
          </Svg>
          <ActiveIcon color="#FFFFFF" active />
        </TouchableOpacity>
      </Animated.View>

      {/* Icon-only hit slots across docked bar */}
      <View style={[styles.tabsRow, { top: TOP_OVERHANG, height: BAR_BASE_HEIGHT }]}>
        {TABS.map(({ key, label, Icon }) => {
          const active = key === activeTab;
          return (
            <TouchableOpacity
              key={key}
              style={styles.tabCell}
              onPress={() => onSelectTab(key)}
              activeOpacity={0.78}
              accessibilityRole="tab"
              accessibilityState={{ selected: active }}
              accessibilityLabel={label}
            >
              {active ? null : <Icon color={theme.ink} active={false} />}
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
});

const styles = StyleSheet.create({
  outerWrap: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
  },
  dockSvgWrap: {
    position: 'absolute',
    left: 0,
    right: 0,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.14,
    shadowRadius: 12,
    elevation: 12,
  },
  orbOuter: {
    position: 'absolute',
    top: 10,
    left: 0,
    width: CIRCLE_SIZE,
    height: CIRCLE_SIZE,
    borderRadius: CIRCLE_SIZE / 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.34,
    shadowRadius: 10,
    elevation: 16,
    zIndex: 6,
  },
  orbTouch: {
    width: CIRCLE_SIZE,
    height: CIRCLE_SIZE,
    borderRadius: CIRCLE_SIZE / 2,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  tabsRow: {
    position: 'absolute',
    left: 0,
    right: 0,
    flexDirection: 'row',
    alignItems: 'center',
    zIndex: 5,
  },
  tabCell: {
    flex: 1,
    height: '100%',
    alignItems: 'center',
    justifyContent: 'center',
  },
});
