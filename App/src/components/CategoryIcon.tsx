import React, { useEffect, useState } from 'react';
import { Image, StyleSheet, View } from 'react-native';

import { useAppTheme } from '../context/ThemeContext';
import { BookOpenIcon } from './Icons';

// eslint-disable-next-line @typescript-eslint/no-var-requires
const CATEGORY_ICONS: Record<string, string> = require('../../assets/category_icons.json');

export function resolveCategoryIconKey(name: string): string {
  const s = (name || '').toLowerCase();
  if (/pre-primary|class\s*[1-5]\b|primary|ebtedayee/.test(s)) return 'primary';
  if (/class\s*([6-9]|10)\b|secondary|dakhil|jsc|ssc/.test(s)) return 'secondary';
  if (/class\s*(11|12)\b|higher secondary|hsc|alim/.test(s)) return 'higher_secondary';
  if (/nctb|teacher guide/.test(s)) return 'nctb';
  if (/computer|programming|python|java|c &|software|database|network|operating|web|cyber|ai|artificial|machine|deep learning|data science|natural language|ict|it /.test(s)) return 'computer';
  if (/engineering|architecture|mechanical|civil|electrical|textile|industrial/.test(s)) return 'engineering';
  if (/medical|dental/.test(s)) return 'medical';
  if (/university|admission|undergraduate|postgraduate|honours|master|mphil|phd|fazil|kamil|gst/.test(s)) return 'university';
  if (/business|accounting|economics|finance|banking|marketing|management|commerce/.test(s)) return 'business';
  if (/math|statistics|formula/.test(s)) return 'math';
  if (/physics/.test(s)) return 'physics';
  if (/chemistry/.test(s)) return 'chemistry';
  if (/biology|biochemistry|environmental/.test(s)) return 'biology';
  if (/science|stem/.test(s)) return 'science';
  if (/history|civilization|liberation war|biograph/.test(s)) return 'history';
  if (/geography|atlas|map/.test(s)) return 'geography';
  if (/madrasa|qawmi|alia|hadith|fiqh|tafsir|quran|aqeedah|islamic|islam|hindu|veda|gita|buddh|tripitaka|christ|bible|religion|scripture/.test(s)) return 'religion';
  if (/author|scholar|writer/.test(s)) return 'authors';
  if (/series|collection|rachanabali|masud|himu|misir/.test(s)) return 'series';
  if (/dictionar|encyclopedia|lexicon/.test(s)) return 'dictionary';
  if (/coaching|udvash|retina|unmesh|10 minute|saifur/.test(s)) return 'coaching';
  if (/exam|board|question|scholarship|model test|suggestion|bcs|job|career|competitive/.test(s)) return 'exam';
  if (/reference|research|journal|publication|thesis|report|handbook|manual|case study/.test(s)) return 'reference';
  if (/philosophy|thought|sociology|psychology|politics|international|law|civics/.test(s)) return 'philosophy';
  if (/novel|poetry|story|literature|essay|drama|thriller|sci-fi|mystery|translation|classic/.test(s)) return 'literature';
  if (/english|grammar|vocabulary|ielts|toefl/.test(s)) return 'english';
  if (/education|textbook|general reading/.test(s)) return 'education';
  if (/review|unclassified|other/.test(s)) return 'archive';
  return 'bangla';
}

interface Props {
  name: string;
  size?: number;
}

export function CategoryIcon({ name, size = 32 }: Props) {
  const { theme } = useAppTheme();
  const key = resolveCategoryIconKey(name);
  const driveId = CATEGORY_ICONS[key] || CATEGORY_ICONS.bangla || CATEGORY_ICONS.education || '';
  const [stage, setStage] = useState<'primary' | 'fallback' | 'vector'>(driveId ? 'primary' : 'vector');

  useEffect(() => {
    setStage(driveId ? 'primary' : 'vector');
  }, [driveId, name]);

  const uri =
    stage === 'primary' && driveId
      ? `https://drive.google.com/thumbnail?id=${encodeURIComponent(driveId)}&sz=w160`
      : stage === 'fallback' && driveId
      ? `https://lh3.googleusercontent.com/d/${encodeURIComponent(driveId)}=w160`
      : '';

  return (
    <View style={[styles.wrap, { width: size, height: size }]}>
      {uri ? (
        <Image
          source={{ uri }}
          style={{ width: size, height: size }}
          resizeMode="contain"
          onError={() => {
            if (stage === 'primary') setStage('fallback');
            else setStage('vector');
          }}
        />
      ) : (
        <BookOpenIcon size={Math.round(size * 0.65)} color={theme.accent} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    alignItems: 'center',
    justifyContent: 'center',
  },
});
