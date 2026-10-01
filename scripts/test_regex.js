const str = `((ItemClass="/Script/Engine.BlueprintGeneratedClass'/Game/FactoryGame/Resource/Parts/IronPlate/Desc_IronPlate.Desc_IronPlate_C'",Amount=2))`;

function parseItemAmounts(s) {
  const results = [];
  // Match Desc_... or BP_...
  const regex = /ItemClass="[^"]*?(?:'|\/)([a-zA-Z0-9_]+)(?:\.[^'"]+)?'",Amount=(\d+(?:\.\d+)?)/g;
  let match;
  while ((match = regex.exec(s)) !== null) {
    results.push({ item: match[1], amount: parseFloat(match[2]) });
  }
  return results;
}

console.log('Result:', parseItemAmounts(str));
