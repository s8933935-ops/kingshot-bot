const fs = require('fs');
const path = require('path');

const dictPath = path.resolve(__dirname, '../../data/processed/dictionary.json');
const dictionary = JSON.parse(fs.readFileSync(dictPath, 'utf8'));

const synonyms = {
  "スパコン": { type: "item", id: "Desc_ComputerSuper_C", name_ja: "スーパーコンピューター", name_en: "Supercomputer" },
  "スーパーコンピュータ": { type: "item", id: "Desc_ComputerSuper_C", name_ja: "スーパーコンピューター", name_en: "Supercomputer" },
  "パソコン": { type: "item", id: "Desc_Computer_C", name_ja: "コンピューター", name_en: "Computer" },
  "コンピューター": { type: "item", id: "Desc_Computer_C", name_ja: "コンピューター", name_en: "Computer" },
  "hmf": { type: "item", id: "Desc_HeavyModularFrame_C", name_ja: "ヘビー・モジュラー・フレーム", name_en: "Heavy Modular Frame" },
  "重モジュ": { type: "item", id: "Desc_HeavyModularFrame_C", name_ja: "ヘビー・モジュラー・フレーム", name_en: "Heavy Modular Frame" },
  "重モジュラー": { type: "item", id: "Desc_HeavyModularFrame_C", name_ja: "ヘビー・モジュラー・フレーム", name_en: "Heavy Modular Frame" },
  "重モジュラーフレーム": { type: "item", id: "Desc_HeavyModularFrame_C", name_ja: "ヘビー・モジュラー・フレーム", name_en: "Heavy Modular Frame" },
  "モジュフレ": { type: "item", id: "Desc_ModularFrame_C", name_ja: "モジュラー・フレーム", name_en: "Modular Frame" },
  "モジュラーフレーム": { type: "item", id: "Desc_ModularFrame_C", name_ja: "モジュラー・フレーム", name_en: "Modular Frame" },
  "強化鉄板": { type: "item", id: "Desc_IronPlateReinforced_C", name_ja: "強化鉄板", name_en: "Reinforced Iron Plate" },
  "rip": { type: "item", id: "Desc_IronPlateReinforced_C", name_ja: "強化鉄板", name_en: "Reinforced Iron Plate" },
  "アルミ": { type: "item", id: "Desc_AluminumPlate_C", name_ja: "アルミニウム・シート", name_en: "Alclad Aluminum Sheet" },
  "アルミシート": { type: "item", id: "Desc_AluminumPlate_C", name_ja: "アルミニウム・シート", name_en: "Alclad Aluminum Sheet" },
  "プラ": { type: "item", id: "Desc_Plastic_C", name_ja: "プラスチック", name_en: "Plastic" },
  "プラスチック": { type: "item", id: "Desc_Plastic_C", name_ja: "プラスチック", name_en: "Plastic" }
};

Object.entries(synonyms).forEach(([term, entry]) => {
  const clean = term.toLowerCase();
  if (!dictionary[clean]) dictionary[clean] = [];
  if (!dictionary[clean].some(e => e.id === entry.id)) {
    dictionary[clean].unshift(entry);
  }
});

fs.writeFileSync(dictPath, JSON.stringify(dictionary, null, 2), 'utf8');
console.log('✅ Added Satisfactory common synonyms to dictionary.json');
