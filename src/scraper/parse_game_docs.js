/**
 * Satisfactory v1.0 Game Docs.json Parser
 * Extracts items, buildings, and recipes with exact Japanese & English metadata.
 */
const fs = require('fs');
const path = require('path');

const STEAM_DOCS_DIR = 'C:\\Program Files (x86)\\Steam\\steamapps\\common\\Satisfactory\\CommunityResources\\Docs';
const JA_FILE = path.join(STEAM_DOCS_DIR, 'ja.json');
const EN_FILE = path.join(STEAM_DOCS_DIR, 'en-US.json');

const OUT_DIR = path.resolve(__dirname, '../../data/processed');

function loadJsonDocs(filePath) {
  const buf = fs.readFileSync(filePath);
  let text = buf.toString('utf16le');
  if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);
  return JSON.parse(text);
}

// Helper: parse ItemClass and Amount from Unreal Engine format
// Example: "((ItemClass=\"/Script/Engine.BlueprintGeneratedClass'/Game/FactoryGame/Resource/Parts/IronIngot/Desc_IronIngot.Desc_IronIngot_C'\",Amount=3))"
function parseItemAmounts(str) {
  if (!str) return [];
  const results = [];
  const regex = /ItemClass="[^"]*?(?:'|\/)([a-zA-Z0-9_]+)(?:\.[^'"]+)?'",Amount=(\d+(?:\.\d+)?)/g;
  let match;
  while ((match = regex.exec(str)) !== null) {
    let rawClass = match[1];
    if (!rawClass.endsWith('_C')) rawClass = `${rawClass}_C`;
    results.push({
      itemClass: rawClass,
      amount: parseFloat(match[2])
    });
  }
  return results;
}

// Helper: parse ProducedIn buildings
function parseProducedIn(str) {
  if (!str) return [];
  const results = [];
  const regex = /(Build_[a-zA-Z0-9_]+)/g;
  let match;
  while ((match = regex.exec(str)) !== null) {
    let rawClass = match[1];
    if (!rawClass.endsWith('_C')) rawClass = `${rawClass}_C`;
    results.push(rawClass);
  }
  return [...new Set(results)];
}

console.log('🚀 Loading Satisfactory v1.0 Official Data...');
const jaDocs = loadJsonDocs(JA_FILE);
const enDocs = loadJsonDocs(EN_FILE);

// Index EN by ClassName for rapid translation lookup
const enMap = new Map();
enDocs.forEach(group => {
  if (Array.isArray(group.Classes)) {
    group.Classes.forEach(cls => {
      enMap.set(cls.ClassName, cls);
    });
  }
});

// 1. Process Items & Resources
console.log('📦 Processing Items and Resources...');
const items = {};
const itemClasses = jaDocs.filter(d => 
  d.NativeClass.includes('ItemDescriptor') || 
  d.NativeClass.includes('ResourceDescriptor')
);

itemClasses.forEach(group => {
  group.Classes.forEach(ja => {
    const en = enMap.get(ja.ClassName) || {};
    // Normalize form
    let form = 'SOLID';
    if (ja.mForm === 'RF_LIQUID') form = 'LIQUID';
    else if (ja.mForm === 'RF_GAS') form = 'GAS';

    // Fluid amounts in docs are stored in thousands (mB or liters), Solid in 1s
    const isFluid = form === 'LIQUID' || form === 'GAS';

    items[ja.ClassName] = {
      id: ja.ClassName,
      name_ja: ja.mDisplayName || '',
      name_en: en.mDisplayName || ja.mDisplayName || '',
      description_ja: (ja.mDescription || '').replace(/\\n/g, '\n').trim(),
      description_en: (en.mDescription || '').replace(/\\n/g, '\n').trim(),
      form,
      is_fluid: isFluid,
      stack_size: parseInt(ja.mCachedStackSize || ja.mStackSize || '100', 10) || 100,
      sink_points: parseInt(ja.mResourceSinkPoints || '0', 10),
      energy_value: parseFloat(ja.mEnergyValue || '0')
    };
  });
});

// 2. Process Buildings & Machines
console.log('🏭 Processing Buildings and Machines...');
const buildings = {};
const buildingClasses = jaDocs.filter(d => d.NativeClass.includes('FGBuildable'));

buildingClasses.forEach(group => {
  group.Classes.forEach(ja => {
    const en = enMap.get(ja.ClassName) || {};
    buildings[ja.ClassName] = {
      id: ja.ClassName,
      name_ja: ja.mDisplayName || '',
      name_en: en.mDisplayName || ja.mDisplayName || '',
      description_ja: (ja.mDescription || '').replace(/\\n/g, '\n').trim(),
      description_en: (en.mDescription || '').replace(/\\n/g, '\n').trim(),
      power_consumption: parseFloat(ja.mPowerConsumption || '0'),
      manufacturing_speed: parseFloat(ja.mManufacturingSpeed || '1')
    };
  });
});

// 3. Process Recipes
console.log('📜 Processing Recipes...');
const recipes = {};
const recipeGroup = jaDocs.find(d => d.NativeClass.includes('FGRecipe'));

if (recipeGroup && Array.isArray(recipeGroup.Classes)) {
  recipeGroup.Classes.forEach(ja => {
    // Exclude build gun / building construction recipes (focus on factory item production recipes)
    const isBuildGun = (ja.mProduct || '').includes('Build_') || (ja.mProduct || '').includes('FGBuildingDescriptor');
    if (isBuildGun) return;

    const en = enMap.get(ja.ClassName) || {};
    const durationSec = parseFloat(ja.mManufactoringDuration || '1');
    const isAlternate = ja.ClassName.includes('Alternate') || (ja.mDisplayName || '').startsWith('代替:') || (ja.mDisplayName || '').startsWith('Alternate:');

    const ingredientsRaw = parseItemAmounts(ja.mIngredients);
    const productsRaw = parseItemAmounts(ja.mProduct);

    if (productsRaw.length === 0) return; // Skip non-product recipes

    const ingredients = ingredientsRaw.map(ing => {
      const itemInfo = items[ing.itemClass] || {};
      const actualAmount = itemInfo.is_fluid ? ing.amount / 1000 : ing.amount;
      const ratePerMin = (actualAmount / durationSec) * 60;
      return {
        item_id: ing.itemClass,
        name_ja: itemInfo.name_ja || ing.itemClass,
        name_en: itemInfo.name_en || ing.itemClass,
        is_fluid: itemInfo.is_fluid || false,
        amount: actualAmount,
        rate_per_min: Math.round(ratePerMin * 1000) / 1000
      };
    });

    const products = productsRaw.map(prod => {
      const itemInfo = items[prod.itemClass] || {};
      const actualAmount = itemInfo.is_fluid ? prod.amount / 1000 : prod.amount;
      const ratePerMin = (actualAmount / durationSec) * 60;
      return {
        item_id: prod.itemClass,
        name_ja: itemInfo.name_ja || prod.itemClass,
        name_en: itemInfo.name_en || prod.itemClass,
        is_fluid: itemInfo.is_fluid || false,
        amount: actualAmount,
        rate_per_min: Math.round(ratePerMin * 1000) / 1000
      };
    });

    const producedInIds = parseProducedIn(ja.mProducedIn);
    const producedInNames = producedInIds.map(bId => {
      const b = buildings[bId];
      return b ? b.name_ja : bId;
    });

    recipes[ja.ClassName] = {
      id: ja.ClassName,
      name_ja: ja.mDisplayName || '',
      name_en: en.mDisplayName || ja.mDisplayName || '',
      is_alternate: isAlternate,
      duration_seconds: durationSec,
      produced_in_ids: producedInIds,
      produced_in_names: producedInNames,
      ingredients,
      products
    };
  });
}

// 4. Build Dictionary / Synonyms Lookup Table
console.log('📖 Generating Japanese-English Bi-directional Dictionary...');
const dictionary = Object.create(null);

function addDictEntry(term, entry) {
  if (!term || typeof term !== 'string') return;
  const clean = term.trim().toLowerCase();
  if (!clean) return;
  if (!Array.isArray(dictionary[clean])) dictionary[clean] = [];
  if (!dictionary[clean].some(e => e.id === entry.id)) {
    dictionary[clean].push(entry);
  }
}

// Populate with Items
Object.values(items).forEach(item => {
  const entry = { type: 'item', id: item.id, name_ja: item.name_ja, name_en: item.name_en };
  addDictEntry(item.name_ja, entry);
  addDictEntry(item.name_en, entry);
  addDictEntry(item.id, entry);
  // Add without spaces or hyphens for fuzzy match
  addDictEntry(item.name_ja.replace(/・|\s+/g, ''), entry);
  addDictEntry(item.name_en.replace(/[-_\s]+/g, ''), entry);
});

// Populate with Recipes
Object.values(recipes).forEach(rec => {
  const entry = { type: 'recipe', id: rec.id, name_ja: rec.name_ja, name_en: rec.name_en, is_alternate: rec.is_alternate };
  addDictEntry(rec.name_ja, entry);
  addDictEntry(rec.name_en, entry);
  addDictEntry(rec.name_ja.replace(/^代替:\s*/, ''), entry);
  addDictEntry(rec.name_en.replace(/^Alternate:\s*/i, ''), entry);
});

// Populate with Buildings
Object.values(buildings).forEach(b => {
  if (!b.name_ja) return;
  const entry = { type: 'building', id: b.id, name_ja: b.name_ja, name_en: b.name_en };
  addDictEntry(b.name_ja, entry);
  addDictEntry(b.name_en, entry);
});

// Write Output Files
fs.writeFileSync(path.join(OUT_DIR, 'items.json'), JSON.stringify(items, null, 2), 'utf8');
fs.writeFileSync(path.join(OUT_DIR, 'buildings.json'), JSON.stringify(buildings, null, 2), 'utf8');
fs.writeFileSync(path.join(OUT_DIR, 'recipes.json'), JSON.stringify(recipes, null, 2), 'utf8');
fs.writeFileSync(path.join(OUT_DIR, 'dictionary.json'), JSON.stringify(dictionary, null, 2), 'utf8');

console.log(`\n🎉 Data Extraction Completed Successfully!`);
console.log(`- Items: ${Object.keys(items).length}`);
console.log(`- Buildings: ${Object.keys(buildings).length}`);
console.log(`- Production Recipes: ${Object.keys(recipes).length}`);
console.log(`- Dictionary Index Keys: ${Object.keys(dictionary).length}`);
console.log(`- Saved to: ${OUT_DIR}`);
