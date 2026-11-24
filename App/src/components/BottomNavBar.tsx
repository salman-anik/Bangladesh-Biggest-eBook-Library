import React, { useMemo, useState } from 'react';
import {
  Dimensions,
  type LayoutChangeEvent,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import Svg, { Circle, Line, Path, Rect } from 'react-native-svg';

import { useAppTheme } from '../context/ThemeContext';
import type { TabKey } from '../types';

interface Props {
  activeTab: TabKey;
  onSelectTab: (tab: TabKey) => void;
  bottomInset?: number;
}

interface TabIconProps {
  color: string;
  active: boolean;
}

const BAR_HEIGHT = 66;
const CIRCLE_SIZE = 54;
const TOP_OVERHANG = 22;
const NOTCH_DEPTH = 29;
const NOTCH_HALF = 35;
const BAR_RADIUS = 20;

function HomeIcon({ color, active }: TabIconProps) {
  return (
    <Svg
      width={active ? 24 : 20}
      height={active ? 24 : 20}
      viewBox="0 0 24 24"
      fill={active ? color : 'none'}
      fillOpacity={active ? 0.24 : 0}
      stroke={color}
      strokeWidth={active ? 2.15 : 1.85}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <Path d="M3 10.5L12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1v-9.5z" />
    </Svg>
  );
}

function LibraryNavIcon({ color, active }: TabIconProps) {
  return (
    <Svg
      width={active ? 24 : 20}
      height={active ? 24 : 20}
      viewBox="0 0 24 24"
      fill={active ? color : 'none'}
      fillOpacity={active ? 0.26 : 0}
      stroke={color}
      strokeWidth={active ? 2.15 : 1.85}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <Path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
    </Svg>
  );
}

function ExploreGridIcon({ color, active }: TabIconProps) {
  return (
    <Svg
      width={active ? 24 : 20}
      height={active ? 24 : 20}
      viewBox="0 0 24 24"
      fill={active ? color : 'none'}
      fillOpacity={active ? 0.24 : 0}
      stroke={color}
      strokeWidth={active ? 2.15 : 1.85}
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
  return (
    <Svg
      width={active ? 24 : 20}
      height={active ? 24 : 20}
      viewBox="0 0 24 24"
      fill={active ? color : 'none'}
      fillOpacity={active ? 0.2 : 0}
      stroke={color}
      strokeWidth={active ? 2.25 : 1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <Circle cx="10.5" cy="10.5" r="7" />
      <Line x1="21" y1="21" x2="15.6" y2="15.6" />
    </Svg>
  );
}

function SettingsNavIcon({ color, active }: TabIconProps) {
  return (
    <Svg
      width={active ? 24 : 20}
      height={active ? 24 : 20}
      viewBox="0 0 24 24"
      fill={active ? color : 'none'}
      fillOpacity={active ? 0.22 : 0}
      stroke={color}
      strokeWidth={active ? 2.15 : 1.85}
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

function buildNotchPath(width: number, cx: number): string {
  const w = Math.max(width, 220);
  const h = BAR_HEIGHT;
  const r = BAR_RADIUS;
  const d = NOTCH_DEPTH;

  const rawLeft = cx - NOTCH_HALF;
  const rawRight = cx + NOTCH_HALF;

  // Guarantee monotonic top coordinates even when the leftmost/rightmost tab is active
  const leftCornerR = rawLeft < r ? Math.max(6, Math.min(r, rawLeft)) : r;
  const rightCornerR = rawRight > w - r ? Math.max(6, Math.min(r, w - rawRight)) : r;
  const leftS = Math.max(leftCornerR, rawLeft);
  const rightS = Math.min(w - rightCornerR, rawRight);

  const lSpan = cx - leftS;
  const rSpan = rightS - cx;

  return [
    `M 0 ${leftCornerR}`,
    `Q 0 0 ${leftCornerR} 0`,
    leftS > leftCornerR ? `L ${leftS.toFixed(2)} 0` : '',
    `C ${(leftS + lSpan * 0.45).toFixed(2)} 0 ${(cx - lSpan * 0.62).toFixed(2)} ${d} ${cx.toFixed(2)} ${d}`,
    `C ${(cx + rSpan * 0.62).toFixed(2)} ${d} ${(rightS - rSpan * 0.45).toFixed(2)} 0 ${rightS.toFixed(2)} 0`,
    rightS < w - rightCornerR ? `L ${(w - rightCornerR).toFixed(2)} 0` : '',
    `Q ${w} 0 ${w} ${rightCornerR}`,
    `L ${w} ${h - r}`,
    `Q ${w} ${h} ${w - r} ${h}`,
    `L ${r} ${h}`,
    `Q 0 ${h} 0 ${h - r}`,
    'Z',
  ]
    .filter(Boolean)
    .join(' ');
}

export function BottomNavBar({ activeTab, onSelectTab, bottomInset = 10 }: Props) {
  const { theme } = useAppTheme();
  const [barWidth, setBarWidth] = useState(() => Math.max(Dimensions.get('window').width - 24, 280));

  const activeIdx = Math.max(
    0,
    TABS.findIndex((t) => t.key === activeTab)
  );
  const tabWidth = barWidth / TABS.length;
  const activeCx = tabWidth * (activeIdx + 0.5);

  const notchPath = useMemo(() => buildNotchPath(barWidth, activeCx), [barWidth, activeCx]);

  const handleLayout = (e: LayoutChangeEvent) => {
    const nextW = Math.round(e.nativeEvent.layout.width);
    if (nextW > 100 && nextW !== barWidth) {
      setBarWidth(nextW);
    }
  };

  const ActiveIcon = TABS[activeIdx]?.Icon || HomeIcon;

  return (
    <View
      style={[styles.outerWrap, { paddingBottom: Math.max(bottomInset, 8) }]}
      pointerEvents="box-none"
    >
      <View style={styles.stageBox} onLayout={handleLayout}>
        {/* Curved Bar Shape */}
        <View style={styles.svgBarShadow}>
          <Svg width={barWidth} height={BAR_HEIGHT}>
            <Path
              d={notchPath}
              fill={theme.surface}
              stroke={theme.border}
              strokeWidth={1.2}
            />
          </Svg>
        </View>

        {/* Elevated Floating Circle Button Centered in Curved Notch */}
        <TouchableOpacity
          style={[
            styles.floatingCircle,
            {
              left: activeCx - CIRCLE_SIZE / 2,
              backgroundColor: theme.surface,
              borderColor: theme.accent,
            },
          ]}
          onPress={() => onSelectTab(TABS[activeIdx].key)}
          activeOpacity={0.9}
          accessibilityRole="tab"
          accessibilityState={{ selected: true }}
          accessibilityLabel={TABS[activeIdx].label}
        >
          <ActiveIcon color={theme.accent} active />
        </TouchableOpacity>

        {/* Tab Hit Areas & Labels inside the Bar */}
        <View style={styles.tabsRow}>
          {TABS.map(({ key, label, Icon }) => {
            const active = key === activeTab;
            return (
              <TouchableOpacity
                key={key}
                style={styles.tabCell}
                onPress={() => onSelectTab(key)}
                activeOpacity={0.8}
                accessibilityRole="tab"
                accessibilityState={{ selected: active }}
                accessibilityLabel={label}
              >
                {active ? (
                  <View style={styles.activeLabelSlot}>
                    <Text
                      style={[styles.activeLabel, { color: theme.ink }]}
                      numberOfLines={1}
                    >
                      {label}
                    </Text>
                  </View>
                ) : (
                  <View style={styles.inactiveContent}>
                    <Icon color={theme.muted} active={false} />
                    <Text
                      style={[styles.inactiveLabel, { color: theme.muted }]}
                      numberOfLines={1}
                    >
                      {label}
                    </Text>
                  </View>
                )}
              </TouchableOpacity>
            );
          })}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  outerWrap: {
    position: 'absolute',
    left: 12,
    right: 12,
    bottom: 0,
    alignItems: 'center',
  },
  stageBox: {
    width: '100%',
    height: TOP_OVERHANG + BAR_HEIGHT,
    position: 'relative',
  },
  svgBarShadow: {
    position: 'absolute',
    left: 0,
    right: 0,
    top: TOP_OVERHANG,
    height: BAR_HEIGHT,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.24,
    shadowRadius: 16,
    elevation: 12,
  },
  floatingCircle: {
    position: 'absolute',
    top: 0,
    width: CIRCLE_SIZE,
    height: CIRCLE_SIZE,
    borderRadius: CIRCLE_SIZE / 2,
    borderWidth: 2.5,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.28,
    shadowRadius: 10,
    elevation: 14,
    zIndex: 5,
  },
  tabsRow: {
    position: 'absolute',
    left: 0,
    right: 0,
    top: TOP_OVERHANG,
    height: BAR_HEIGHT,
    flexDirection: 'row',
    alignItems: 'center',
    zIndex: 4,
  },
  tabCell: {
    flex: 1,
    height: '100%',
    alignItems: 'center',
    justifyContent: 'center',
  },
  activeLabelSlot: {
    height: '100%',
    justifyContent: 'flex-end',
    paddingBottom: 12,
  },
  activeLabel: {
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0.15,
  },
  inactiveContent: {
    alignItems: 'center',
    justifyContent: 'center',
    gap: 3,
  },
  inactiveLabel: {
    fontSize: 10.5,
    fontWeight: '600',
    letterSpacing: 0.1,
  },
});
