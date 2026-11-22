const BANGLA_DIGITS = ['০', '১', '২', '৩', '৪', '৫', '৬', '৭', '৮', '৯'] as const;

const BANGLA_MONTHS = [
  'জানুয়ারি',
  'ফেব্রুয়ারি',
  'মার্চ',
  'এপ্রিল',
  'মে',
  'জুন',
  'জুলাই',
  'আগস্ট',
  'সেপ্টেম্বর',
  'অক্টোবর',
  'নভেম্বর',
  'ডিসেম্বর',
] as const;

export function toBanglaDigits(input: number | string): string {
  return String(input).replace(/\d/g, (digit) => BANGLA_DIGITS[Number(digit)]);
}

export function formatBanglaDate(dateInput: Date | string): string {
  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
  if (Number.isNaN(date.getTime())) {
    return String(dateInput);
  }
  const day = toBanglaDigits(date.getUTCDate());
  const month = BANGLA_MONTHS[date.getUTCMonth()];
  const year = toBanglaDigits(date.getUTCFullYear());
  return `${day} ${month} ${year}`;
}

export function estimateReadingTimeMinutes(text: string): number {
  const cleaned = text
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/[#>*_`~\[\]()!-]/g, ' ')
    .trim();
  if (!cleaned) return 1;
  const words = cleaned.split(/\s+/).filter(Boolean).length;
  // Average careful reading speed for scientific Bangla prose (~165 words/min)
  return Math.max(1, Math.ceil(words / 165));
}

export function formatReadingTimeBn(minutes: number): string {
  return `${toBanglaDigits(minutes)} মিনিট পাঠ`;
}

export type ResearchType = 'original-research' | 'review' | 'preprint' | 'editorial';
export type PublicationStatus = 'peer-reviewed' | 'preprint' | 'editorial-summary';
export type StudyModel =
  | 'in-vitro'
  | 'animal'
  | 'human-observational'
  | 'human-clinical'
  | 'computational'
  | 'field-ecology'
  | 'multi-study';

export const RESEARCH_TYPE_LABELS: Record<
  ResearchType,
  { labelBn: string; labelEn: string; badgeClass: string }
> = {
  'original-research': {
    labelBn: 'মৌলিক গবেষণা',
    labelEn: 'Original Research',
    badgeClass: 'bg-teal-50 text-teal-900 border-teal-200',
  },
  review: {
    labelBn: 'পর্যালোচনামূলক প্রবন্ধ',
    labelEn: 'Review Article',
    badgeClass: 'bg-sky-50 text-sky-900 border-sky-200',
  },
  preprint: {
    labelBn: 'প্রিপ্রিন্ট (অ-পর্যালোচিত)',
    labelEn: 'Preprint (Not Peer-Reviewed)',
    badgeClass: 'bg-amber-50 text-amber-900 border-amber-300',
  },
  editorial: {
    labelBn: 'সম্পাদকীয় বিশ্লেষণ',
    labelEn: 'Editorial Synthesis',
    badgeClass: 'bg-slate-100 text-slate-800 border-slate-300',
  },
};

export const STUDY_MODEL_LABELS: Record<StudyModel, string> = {
  'in-vitro': 'গবেষণাগারে কোষীয় পরীক্ষা (In-vitro)',
  animal: 'প্রাণী মডেলের গবেষণা (Animal Study)',
  'human-observational': 'মানব পর্যবেক্ষণমূলক গবেষণা (Observational)',
  'human-clinical': 'মানব ক্লিনিক্যাল গবেষণা (Clinical Study)',
  computational: 'কম্পিউটেশনাল ও জিনোমিক বিশ্লেষণ (Genomic / In-silico)',
  'field-ecology': 'মাঠপর্যায়ের বাস্তুতান্ত্রিক গবেষণা (Field Study)',
  'multi-study': 'বহুমাত্রিক বৈজ্ঞানিক প্রমাণ সংশ্লেষণ',
};
