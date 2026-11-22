export interface CategoryMeta {
  slug: CategorySlug;
  nameBn: string;
  nameEn: string;
  illustration: IllustrationMotif;
  descriptionBn: string;
  shortNoteBn: string;
}

export const CATEGORY_SLUGS = [
  'microbiology',
  'biotechnology',
  'genetics-genomics',
  'biomedical-science',
  'immunology',
  'environment-biodiversity',
  'marine-biology',
  'botany',
  'zoology',
  'evolution',
] as const;

export type CategorySlug = (typeof CATEGORY_SLUGS)[number];

export type IllustrationMotif =
  | 'microbe'
  | 'crispr'
  | 'dna'
  | 'cell'
  | 'antibody'
  | 'ecosystem'
  | 'marine'
  | 'leaf'
  | 'zoology'
  | 'phylogeny';

export const CATEGORIES: Record<CategorySlug, CategoryMeta> = {
  microbiology: {
    slug: 'microbiology',
    nameBn: 'অণুজীববিজ্ঞান',
    nameEn: 'Microbiology',
    illustration: 'microbe',
    descriptionBn:
      'ব্যাকটেরিয়া, ভাইরাস, ছত্রাক, আর্কিয়া, অ্যান্টিবায়োটিক রেজিস্ট্যান্স এবং মানবদেহ ও প্রকৃতির মাইক্রোবায়োম বিষয়ক পিয়ার-রিভিউকৃত ও প্রাক-মুদ্রিত গবেষণার সহজ বাংলা ব্যাখ্যা।',
    shortNoteBn: 'ব্যাকটেরিয়া, ভাইরাস, ফাজ ও মাইক্রোবায়োম গবেষণা',
  },
  biotechnology: {
    slug: 'biotechnology',
    nameBn: 'জীবপ্রযুক্তি',
    nameEn: 'Biotechnology',
    illustration: 'crispr',
    descriptionBn:
      'CRISPR জিন সম্পাদনা, সিনথেটিক বায়োলজি, জৈবপ্রকৌশল, এনজাইম প্রযুক্তি এবং কৃষি ও পরিবেশবান্ধব শিল্পে জীবপ্রযুক্তির নতুন উদ্ভাবন।',
    shortNoteBn: 'জিন সম্পাদনা, সিনথেটিক বায়োলজি ও জৈবপ্রকৌশল',
  },
  'genetics-genomics': {
    slug: 'genetics-genomics',
    nameBn: 'জিনতত্ত্ব ও জিনোমিক্স',
    nameEn: 'Genetics & Genomics',
    illustration: 'dna',
    descriptionBn:
      'ডিএনএ, আরএনএ, পূর্ণাঙ্গ জিনোম সিকোয়েন্সিং, এপিজেনেটিক্স, জিন প্রকাশ নিয়ন্ত্রণ এবং বংশগতির আণবিক ভিত্তি সম্পর্কিত মৌলিক গবেষণা।',
    shortNoteBn: 'ডিএনএ, আরএনএ, এপিজেনেটিক্স ও জিনোম সিকোয়েন্সিং',
  },
  'biomedical-science': {
    slug: 'biomedical-science',
    nameBn: 'চিকিৎসা জীববিজ্ঞান',
    nameEn: 'Biomedical Science',
    illustration: 'cell',
    descriptionBn:
      'মানবদেহের কোষীয় প্রক্রিয়া, স্নায়ুবিজ্ঞান, স্টেম সেল, ক্যান্সার জীববিজ্ঞান এবং প্রাক-ক্লিনিক্যাল ও ক্লিনিক্যাল গবেষণার তথ্যনিষ্ঠ বিশ্লেষণ।',
    shortNoteBn: 'কোষতত্ত্ব, স্নায়ুবিজ্ঞান ও রোগতত্ত্বের আণবিক ভিত্তি',
  },
  immunology: {
    slug: 'immunology',
    nameBn: 'রোগপ্রতিরোধবিদ্যা',
    nameEn: 'Immunology',
    illustration: 'antibody',
    descriptionBn:
      'দেহের সহজাত ও অর্জিত প্রতিরক্ষা ব্যবস্থা, টি-কোষ, বি-কোষ, অ্যান্টিবডি, টিকা বিজ্ঞান এবং অটোইমিউন প্রতিক্রিয়া নিয়ে গবেষণা।',
    shortNoteBn: 'টি-কোষ, অ্যান্টিবডি, টিকা বিজ্ঞান ও প্রতিরক্ষা ব্যবস্থা',
  },
  'environment-biodiversity': {
    slug: 'environment-biodiversity',
    nameBn: 'পরিবেশ ও জীববৈচিত্র্য',
    nameEn: 'Environment & Biodiversity',
    illustration: 'ecosystem',
    descriptionBn:
      'বাস্তুতন্ত্রের ভারসাম্য, সংরক্ষণ জীববিজ্ঞান, জলবায়ু পরিবর্তনের জৈবিক প্রভাব, পরাগায়ন এবং বিপন্ন প্রজাতি সংরক্ষণ বিষয়ক গবেষণা।',
    shortNoteBn: 'বাস্তুতন্ত্র, সংরক্ষণ জীববিজ্ঞান ও জলবায়ু প্রভাব',
  },
  'marine-biology': {
    slug: 'marine-biology',
    nameBn: 'সামুদ্রিক জীববিজ্ঞান',
    nameEn: 'Marine Biology',
    illustration: 'marine',
    descriptionBn:
      'মহাসাগর ও উপকূলীয় জীবজগৎ, প্রবাল প্রাচীরের তাপসহনশীলতা, প্ল্যাঙ্কটন, ম্যানগ্রোভ এবং গভীর সমুদ্রের বিস্ময়কর জীবের বৈজ্ঞানিক অনুসন্ধান।',
    shortNoteBn: 'প্রবাল প্রাচীর, প্ল্যাঙ্কটন ও গভীর সমুদ্রের জীবজগৎ',
  },
  botany: {
    slug: 'botany',
    nameBn: 'উদ্ভিদবিজ্ঞান',
    nameEn: 'Botany',
    illustration: 'leaf',
    descriptionBn:
      'উদ্ভিদের শারীরতত্ত্ব, সালোকসংশ্লেষণ, স্টোমাটা ও খরা সহনশীলতা, উদ্ভিদ-অণুজীব মিথস্ক্রিয়া এবং ফসলের জিনগত অভিযোজন।',
    shortNoteBn: 'সালোকসংশ্লেষণ, উদ্ভিদ শারীরতত্ত্ব ও কৃষি জীববিজ্ঞান',
  },
  zoology: {
    slug: 'zoology',
    nameBn: 'প্রাণিবিজ্ঞান',
    nameEn: 'Zoology',
    illustration: 'zoology',
    descriptionBn:
      'অমেরুদণ্ডী ও মেরুদণ্ডী প্রাণীর অঙ্গসংস্থান, আচরণবিদ্যা, পরিযান, পুনরুৎপাদন সক্ষমতা এবং শারীরবৃত্তীয় অভিযোজন নিয়ে গবেষণা।',
    shortNoteBn: 'প্রাণীর আচরণ, অঙ্গসংস্থান ও শারীরবৃত্তীয় অভিযোজন',
  },
  evolution: {
    slug: 'evolution',
    nameBn: 'বিবর্তন জীববিজ্ঞান',
    nameEn: 'Evolution',
    illustration: 'phylogeny',
    descriptionBn:
      'প্রাকৃতিক নির্বাচন, প্রজাতির উৎপত্তি, প্রাচীন ডিএনএ (প্যালিওজিনোমিক্স), জীবাশ্মবিদ্যা এবং ফাইলোজেনেটিক বিবর্তন বৃক্ষের গবেষণা।',
    shortNoteBn: 'প্রাকৃতিক নির্বাচন, প্রাচীন ডিএনএ ও প্রজাতির বিবর্তন',
  },
};

export const CATEGORY_LIST: CategoryMeta[] = CATEGORY_SLUGS.map((slug) => CATEGORIES[slug]);

export function getCategoryMeta(slug: string): CategoryMeta {
  if (slug in CATEGORIES) {
    return CATEGORIES[slug as CategorySlug];
  }
  return CATEGORIES['biomedical-science'];
}
