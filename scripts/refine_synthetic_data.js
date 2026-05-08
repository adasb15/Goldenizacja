const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const DATA_DIR = path.join(ROOT, "data");
const FORMATS = ["csv", "json", "xml", "xlsx"];
const TARGET_PER_REGISTER = 800;
const TARGET_PER_FORMAT = TARGET_PER_REGISTER / FORMATS.length;
const RNG_SEED = 20260507;

const ADDRESSES = [
  ["MAZOWIECKIE", "WARSZAWA", "WARSZAWA", "WARSZAWA", "Warszawa", "Marszałkowska", "00-590"],
  ["MAZOWIECKIE", "WARSZAWA", "WARSZAWA", "WARSZAWA", "Warszawa", "Krakowskie Przedmieście", "00-071"],
  ["MAŁOPOLSKIE", "KRAKÓW", "KRAKÓW", "KRAKÓW", "Kraków", "Floriańska", "31-019"],
  ["MAŁOPOLSKIE", "KRAKÓW", "KRAKÓW", "KRAKÓW", "Kraków", "Długa", "31-147"],
  ["ŁÓDZKIE", "ŁÓDŹ", "ŁÓDŹ", "ŁÓDŹ", "Łódź", "Piotrkowska", "90-102"],
  ["ŁÓDZKIE", "ŁÓDŹ", "ŁÓDŹ", "ŁÓDŹ", "Łódź", "Zachodnia", "90-402"],
  ["DOLNOŚLĄSKIE", "WROCŁAW", "WROCŁAW", "WROCŁAW", "Wrocław", "Świdnicka", "50-066"],
  ["DOLNOŚLĄSKIE", "WROCŁAW", "WROCŁAW", "WROCŁAW", "Wrocław", "Legnicka", "54-203"],
  ["WIELKOPOLSKIE", "POZNAŃ", "POZNAŃ", "POZNAŃ", "Poznań", "Święty Marcin", "61-806"],
  ["WIELKOPOLSKIE", "POZNAŃ", "POZNAŃ", "POZNAŃ", "Poznań", "Głogowska", "60-734"],
  ["POMORSKIE", "GDAŃSK", "GDAŃSK", "GDAŃSK", "Gdańsk", "Długa", "80-831"],
  ["POMORSKIE", "GDAŃSK", "GDAŃSK", "GDAŃSK", "Gdańsk", "Grunwaldzka", "80-236"],
  ["ZACHODNIOPOMORSKIE", "SZCZECIN", "SZCZECIN", "SZCZECIN", "Szczecin", "Jagiellońska", "70-435"],
  ["ZACHODNIOPOMORSKIE", "SZCZECIN", "SZCZECIN", "SZCZECIN", "Szczecin", "Wyszyńskiego", "70-200"],
  ["ŚLĄSKIE", "KATOWICE", "KATOWICE", "KATOWICE", "Katowice", "Mariacka", "40-014"],
  ["ŚLĄSKIE", "KATOWICE", "KATOWICE", "KATOWICE", "Katowice", "Warszawska", "40-009"],
  ["LUBELSKIE", "LUBLIN", "LUBLIN", "LUBLIN", "Lublin", "Krakowskie Przedmieście", "20-002"],
  ["LUBELSKIE", "LUBLIN", "LUBLIN", "LUBLIN", "Lublin", "Narutowicza", "20-004"],
  ["PODLASKIE", "BIAŁYSTOK", "BIAŁYSTOK", "BIAŁYSTOK", "Białystok", "Lipowa", "15-424"],
  ["PODLASKIE", "BIAŁYSTOK", "BIAŁYSTOK", "BIAŁYSTOK", "Białystok", "Sienkiewicza", "15-092"],
  ["KUJAWSKO-POMORSKIE", "BYDGOSZCZ", "BYDGOSZCZ", "BYDGOSZCZ", "Bydgoszcz", "Gdańska", "85-005"],
  ["KUJAWSKO-POMORSKIE", "BYDGOSZCZ", "BYDGOSZCZ", "BYDGOSZCZ", "Bydgoszcz", "Dworcowa", "85-009"],
  ["KUJAWSKO-POMORSKIE", "TORUŃ", "TORUŃ", "TORUŃ", "Toruń", "Szeroka", "87-100"],
  ["KUJAWSKO-POMORSKIE", "TORUŃ", "TORUŃ", "TORUŃ", "Toruń", "Chełmińska", "87-100"],
  ["PODKARPACKIE", "RZESZÓW", "RZESZÓW", "RZESZÓW", "Rzeszów", "3 Maja", "35-030"],
  ["PODKARPACKIE", "RZESZÓW", "RZESZÓW", "RZESZÓW", "Rzeszów", "Piłsudskiego", "35-074"],
  ["ŚWIĘTOKRZYSKIE", "KIELCE", "KIELCE", "KIELCE", "Kielce", "Sienkiewicza", "25-007"],
  ["ŚWIĘTOKRZYSKIE", "KIELCE", "KIELCE", "KIELCE", "Kielce", "Warszawska", "25-512"],
  ["WARMIŃSKO-MAZURSKIE", "OLSZTYN", "OLSZTYN", "OLSZTYN", "Olsztyn", "Kościuszki", "10-504"],
  ["WARMIŃSKO-MAZURSKIE", "OLSZTYN", "OLSZTYN", "OLSZTYN", "Olsztyn", "Dąbrowszczaków", "10-540"],
  ["OPOLSKIE", "OPOLE", "OPOLE", "OPOLE", "Opole", "Krakowska", "45-018"],
  ["OPOLSKIE", "OPOLE", "OPOLE", "OPOLE", "Opole", "Ozimska", "45-057"],
  ["LUBUSKIE", "ZIELONA GÓRA", "ZIELONA GÓRA", "ZIELONA GÓRA", "Zielona Góra", "Bohaterów Westerplatte", "65-034"],
  ["LUBUSKIE", "ZIELONA GÓRA", "ZIELONA GÓRA", "ZIELONA GÓRA", "Zielona Góra", "Kupiecka", "65-058"],
  ["POMORSKIE", "GDYNIA", "GDYNIA", "GDYNIA", "Gdynia", "Świętojańska", "81-372"],
  ["POMORSKIE", "GDYNIA", "GDYNIA", "GDYNIA", "Gdynia", "10 Lutego", "81-364"],
  ["MAZOWIECKIE", "PRUSZKOWSKI", "PRUSZK\u00d3W", "PRUSZK\u00d3W", "Pruszk\u00f3w", "Boles\u0142awa Prusa", "05-800"],
  ["MAZOWIECKIE", "PIASECZY\u0143SKI", "PIASECZNO", "PIASECZNO", "Piaseczno", "Ko\u015bciuszki", "05-500"],
  ["MA\u0141OPOLSKIE", "WIELICKI", "WIELICZKA", "WIELICZKA", "Wieliczka", "Sienkiewicza", "32-020"],
  ["MA\u0141OPOLSKIE", "O\u015aWI\u0118CIMSKI", "O\u015aWI\u0118CIM", "O\u015aWI\u0118CIM", "O\u015bwi\u0119cim", "D\u0105browskiego", "32-600"],
  ["PODKARPACKIE", "KRO\u015aNIE\u0143SKI", "KROSNO", "KROSNO", "Krosno", "Rynek", "38-400"],
  ["PODKARPACKIE", "MIELECKI", "MIELEC", "MIELEC", "Mielec", "Mickiewicza", "39-300"],
  ["DOLNO\u015aL\u0104SKIE", "\u015aWIDNICKI", "\u015aWIDNICA", "\u015aWIDNICA", "\u015awidnica", "D\u0142uga", "58-100"],
  ["DOLNO\u015aL\u0104SKIE", "K\u0141ODZKI", "K\u0141ODZKO", "K\u0141ODZKO", "K\u0142odzko", "Wojska Polskiego", "57-300"],
  ["WIELKOPOLSKIE", "GNIE\u0179NIE\u0143SKI", "GNIEZNO", "GNIEZNO", "Gniezno", "Chrobrego", "62-200"],
  ["WIELKOPOLSKIE", "LESZCZY\u0143SKI", "LESZNO", "LESZNO", "Leszno", "S\u0142owia\u0144ska", "64-100"],
  ["POMORSKIE", "TCZEWSKI", "TCZEW", "TCZEW", "Tczew", "Gda\u0144ska", "83-110"],
  ["POMORSKIE", "WEJHEROWSKI", "WEJHEROWO", "WEJHEROWO", "Wejherowo", "Sobieskiego", "84-200"],
  ["\u015aL\u0104SKIE", "CIESZY\u0143SKI", "CIESZYN", "CIESZYN", "Cieszyn", "G\u0142\u0119boka", "43-400"],
  ["\u015aL\u0104SKIE", "B\u0118DZI\u0143SKI", "B\u0118DZIN", "B\u0118DZIN", "B\u0119dzin", "Ma\u0142achowskiego", "42-500"],
  ["KUJAWSKO-POMORSKIE", "INOWROC\u0141AWSKI", "INOWROC\u0141AW", "INOWROC\u0141AW", "Inowroc\u0142aw", "Kr\u00f3lowej Jadwigi", "88-100"],
  ["KUJAWSKO-POMORSKIE", "GRUDZI\u0104DZ", "GRUDZI\u0104DZ", "GRUDZI\u0104DZ", "Grudzi\u0105dz", "Wybickiego", "86-300"],
  ["WARMI\u0143SKO-MAZURSKIE", "OSTR\u00d3DZKI", "OSTR\u00d3DA", "OSTR\u00d3DA", "Ostr\u00f3da", "Czarnieckiego", "14-100"],
  ["WARMI\u0143SKO-MAZURSKIE", "GI\u017bYCKI", "GI\u017bYCKO", "GI\u017bYCKO", "Gi\u017cycko", "Warszawska", "11-500"],
  ["LUBELSKIE", "PU\u0141AWSKI", "PU\u0141AWY", "PU\u0141AWY", "Pu\u0142awy", "Lubelska", "24-100"],
  ["LUBELSKIE", "ZAMO\u015a\u0106", "ZAMO\u015a\u0106", "ZAMO\u015a\u0106", "Zamo\u015b\u0107", "Staszica", "22-400"],
  ["PODLASKIE", "AUGUSTOWSKI", "AUGUST\u00d3W", "AUGUST\u00d3W", "August\u00f3w", "3 Maja", "16-300"],
  ["PODLASKIE", "SUWA\u0141KI", "SUWA\u0141KI", "SUWA\u0141KI", "Suwa\u0142ki", "Ko\u015bciuszki", "16-400"],
  ["OPOLSKIE", "NYSA", "NYSA", "NYSA", "Nysa", "Piastowska", "48-300"],
  ["OPOLSKIE", "BRZESKI", "BRZEG", "BRZEG", "Brzeg", "D\u0142uga", "49-300"],
  ["LUBUSKIE", "\u017bARSKI", "\u017bARY", "\u017bARY", "\u017bary", "Rynek", "68-200"],
  ["LUBUSKIE", "\u015aWIEBODZI\u0143SKI", "\u015aWIEBODZIN", "\u015aWIEBODZIN", "\u015awiebodzin", "Sikorskiego", "66-200"],
  ["ZACHODNIOPOMORSKIE", "KO\u0141OBRZESKI", "KO\u0141OBRZEG", "KO\u0141OBRZEG", "Ko\u0142obrzeg", "Armii Krajowej", "78-100"],
  ["ZACHODNIOPOMORSKIE", "STARGARDZKI", "STARGARD", "STARGARD", "Stargard", "Pi\u0142sudskiego", "73-110"],
  ["\u015aWI\u0118TOKRZYSKIE", "SANDOMIERSKI", "SANDOMIERZ", "SANDOMIERZ", "Sandomierz", "Mickiewicza", "27-600"],
  ["\u015aWI\u0118TOKRZYSKIE", "OSTROWIECKI", "OSTROWIEC \u015aWI\u0118TOKRZYSKI", "OSTROWIEC \u015aWI\u0118TOKRZYSKI", "Ostrowiec \u015awi\u0119tokrzyski", "Sienkiewicza", "27-400"],
];

const FEMALE_FIRST_NAMES = ["Anna", "Maria", "Katarzyna", "Joanna", "Ewa", "Magdalena", "Monika", "Agnieszka", "Barbara", "Justyna"];
const MALE_FIRST_NAMES = ["Piotr", "Tomasz", "Michał", "Krzysztof", "Paweł", "Adam", "Robert", "Marek", "Wojciech", "Rafał"];
const LAST_NAME_PAIRS = [
  ["Kowalska", "Kowalski"],
  ["Nowacka", "Nowacki"],
  ["Wiśniewska", "Wiśniewski"],
  ["Wójcik", "Wójcik"],
  ["Kowalczyk", "Kowalczyk"],
  ["Kamińska", "Kamiński"],
  ["Lewandowska", "Lewandowski"],
  ["Zielińska", "Zieliński"],
  ["Szymańska", "Szymański"],
  ["Dąbrowska", "Dąbrowski"],
  ["Mazur", "Mazur"],
  ["Krawczyk", "Krawczyk"],
  ["Wo\u017aniak", "Wo\u017aniak"],
  ["Jankowska", "Jankowski"],
  ["Grabowska", "Grabowski"],
  ["Pawlak", "Pawlak"],
  ["Michalska", "Michalski"],
  ["Kr\u00f3l", "Kr\u00f3l"],
  ["Wieczorek", "Wieczorek"],
  ["Jab\u0142o\u0144ska", "Jab\u0142o\u0144ski"],
  ["Witkowska", "Witkowski"],
  ["Walczak", "Walczak"],
  ["St\u0119pie\u0144", "St\u0119pie\u0144"],
  ["Baran", "Baran"],
  ["Rutkowska", "Rutkowski"],
  ["G\u00f3rska", "G\u00f3rski"],
  ["Sikora", "Sikora"],
  ["Ostrowska", "Ostrowski"],
  ["Tomaszewska", "Tomaszewski"],
  ["Zaj\u0105c", "Zaj\u0105c"],
  ["Pietrzak", "Pietrzak"],
  ["W\u00f3jcicka", "W\u00f3jcicki"],
  ["Czarnecka", "Czarnecki"],
  ["Lis", "Lis"],
  ["Ko\u0142odziej", "Ko\u0142odziej"],
  ["Kaczmarek", "Kaczmarek"],
  ["Pi\u0105tek", "Pi\u0105tek"],
  ["Sadowska", "Sadowski"],
  ["W\u0142odarczyk", "W\u0142odarczyk"],
  ["Borkowska", "Borkowski"],
];
const COMPANY_BASE = ["Astra Finance", "Baltic Med Supply", "Helios Markets", "Lumen Advisory", "Nova Data", "Optima Trade", "Polaris Capital", "Quantum Services", "Silesia Invest", "Vistula Fintech"];
const COMPANY_SUFFIXES = [
  "sp. z o.o.",
  "sp z oo",
  "sp. z o. o.",
  "Sp. z o.o.",
  "SP Z O O",
  "sp\u00f3\u0142ka z ograniczon\u0105 odpowiedzialno\u015bci\u0105",
  "Sp\u00f3\u0142ka z ograniczon\u0105 odpowiedzialno\u015bci\u0105",
  "S.A.",
  "SA",
  "S. A.",
  "Sp\u00f3\u0142ka Akcyjna",
];
const LEGAL_FORM_VARIANTS = [
  "sp\u00f3\u0142ka z ograniczon\u0105 odpowiedzialno\u015bci\u0105",
  "sp. z o.o.",
  "sp z oo",
  "SP Z O O",
  "sp\u00f3\u0142ka akcyjna",
  "S.A.",
  "SA",
  "prosta sp\u00f3\u0142ka akcyjna",
  "osoba fizyczna prowadz\u0105ca dzia\u0142alno\u015b\u0107 gospodarcz\u0105",
];
const STREET_PREFIXES = ["ul.", "ul", "ulica", ""];
const MAIL_DOMAINS = ["finanse.pl", "biuro.pl", "kancelaria.pl", "ubezpieczenia.pl", "broker.local", "firma.local"];
const PERSON_MAIL_DOMAINS = ["poczta.pl", "mail.pl", "onet.pl", "wp.pl", "gmail.com", "proton.me", "biuro.pl"];
const WEB_TLDS = [".pl", ".com.pl", ".eu", ".local"];
const HOUSE_NUMBER_ONLY_CITIES = new Set([
  "Wieliczka",
  "Krosno",
  "Mielec",
  "\u015awidnica",
  "K\u0142odzko",
  "Tczew",
  "Wejherowo",
  "Cieszyn",
  "B\u0119dzin",
  "Ostr\u00f3da",
  "Gi\u017cycko",
  "Pu\u0142awy",
  "August\u00f3w",
  "\u017bary",
  "\u015awiebodzin",
  "Sandomierz",
]);

let rngState = RNG_SEED >>> 0;
function rand() {
  rngState = (1664525 * rngState + 1013904223) >>> 0;
  return rngState / 0x100000000;
}

function pick(items, index) {
  return items[index % items.length];
}

function keyId(value) {
  return String(value)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
}

function transliteratePolish(value) {
  const map = {
    "\u0105": "a", "\u0107": "c", "\u0119": "e", "\u0142": "l", "\u0144": "n", "\u00f3": "o", "\u015b": "s", "\u017a": "z", "\u017c": "z",
    "\u0104": "A", "\u0106": "C", "\u0118": "E", "\u0141": "L", "\u0143": "N", "\u00d3": "O", "\u015a": "S", "\u0179": "Z", "\u017b": "Z",
  };
  return String(value ?? "").replace(/[\u0105\u0107\u0119\u0142\u0144\u00f3\u015b\u017a\u017c\u0104\u0106\u0118\u0141\u0143\u00d3\u015a\u0179\u017b]/g, (char) => map[char] || char);
}

function isFemaleIndex(index) {
  return index % 2 === 0;
}

function personFor(index, female) {
  const firstNames = female ? FEMALE_FIRST_NAMES : MALE_FIRST_NAMES;
  const lastPair = pick(LAST_NAME_PAIRS, index);
  return {
    first: pick(firstNames, index),
    second: index % 3 === 0 ? "" : pick(firstNames, index + 5),
    last: female ? lastPair[0] : lastPair[1],
  };
}

function familyNameFor(index, female) {
  if (female && index % 3 !== 0) return pick(LAST_NAME_PAIRS, index + 9)[0];
  if (!female && index % 8 === 0) return pick(LAST_NAME_PAIRS, index + 9)[1];
  return "";
}

function slug(value, separator = ".") {
  return transliteratePolish(value)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, separator)
    .replace(new RegExp(`\\${separator}+`, "g"), separator)
    .replace(new RegExp(`^\\${separator}|\\${separator}$`, "g"), "");
}

function companySlug(value) {
  return slug(value, "-")
    .replace(/-spolka-z-ograniczona-odpowiedzialnoscia|-sp-z-o-o|-sp-z-oo|-sa|-s-a|-spolka-akcyjna|-sp-z-o-o/g, "")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

function emailForPerson(index, companyBase, person) {
  const domainBase = companySlug(companyBase) || "firma";
  const domain = index % 4 === 0
    ? `${domainBase}${pick(WEB_TLDS, index)}`
    : pick(PERSON_MAIL_DOMAINS, index);
  const first = slug(person.first);
  const last = slug(person.last);
  const variants = [
    `${first}.${last}`,
    `${first[0]}.${last}`,
    `${last}.${first}`,
    `${first}${last}`,
    `${first}_${last}`,
    `${first}.${last}${String(70 + (index % 29))}`,
  ];
  return `${pick(variants, index)}@${domain}`;
}

function emailForCompany(index, companyBase) {
  const domainBase = companySlug(companyBase) || "firma";
  const domain = index % 4 === 0
    ? `${domainBase}${pick(WEB_TLDS, index)}`
    : pick(MAIL_DOMAINS, index);
  const variants = [
    `kontakt.${domainBase}`,
    `biuro.${domainBase}`,
    `sekretariat.${domainBase}`,
    `firma.${domainBase}`,
    `kontakt`,
    `biuro`,
    `office.${domainBase}`,
  ];
  return `${pick(variants, index)}@${domain}`;
}

function websiteFor(index, companyBase) {
  const base = companySlug(companyBase) || "firma";
  const host = index % 5 === 0 ? `www.${base}` : index % 5 === 1 ? base : `www.${base}-group`;
  return `https://${host}${pick(WEB_TLDS, index + 1)}`;
}

function pad(num, len) {
  return String(num).padStart(len, "0");
}

function xmlEscape(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function xmlUnescape(value) {
  return String(value ?? "")
    .replace(/&quot;/g, '"')
    .replace(/&gt;/g, ">")
    .replace(/&lt;/g, "<")
    .replace(/&amp;/g, "&");
}

function parseCsv(content) {
  if (content.charCodeAt(0) === 0xfeff) content = content.slice(1);
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < content.length; i += 1) {
    const ch = content[i];
    if (quoted) {
      if (ch === '"' && content[i + 1] === '"') {
        field += '"';
        i += 1;
      } else if (ch === '"') {
        quoted = false;
      } else {
        field += ch;
      }
    } else if (ch === '"') {
      quoted = true;
    } else if (ch === ",") {
      row.push(field);
      field = "";
    } else if (ch === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else if (ch !== "\r") {
      field += ch;
    }
  }
  if (field.length || row.length) {
    row.push(field);
    rows.push(row);
  }
  const headers = rows.shift() || [];
  return {
    headers,
    records: rows.filter((r) => r.length > 1 || r[0]).map((r) => Object.fromEntries(headers.map((h, i) => [h, r[i] ?? ""]))),
  };
}

function stringifyCsv(headers, records) {
  const line = (values) => values.map((value) => {
    const text = String(value ?? "");
    return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  }).join(",");
  return `\ufeff${line(headers)}\r\n${records.map((record) => line(headers.map((h) => record[h] ?? ""))).join("\r\n")}\r\n`;
}

function parseXmlRecords(filePath) {
  if (!fs.existsSync(filePath)) return [];
  const content = fs.readFileSync(filePath, "utf8");
  const records = [];
  for (const match of content.matchAll(/<record>([\s\S]*?)<\/record>/g)) {
    const record = {};
    for (const field of match[1].matchAll(/<field name="([^"]*)">([\s\S]*?)<\/field>/g)) {
      record[xmlUnescape(field[1])] = xmlUnescape(field[2]);
    }
    records.push(record);
  }
  return records;
}

function readRecords(register) {
  const csvPath = path.join(DATA_DIR, "csv", `${register}.csv`);
  const { headers, records } = parseCsv(fs.readFileSync(csvPath, "utf8"));
  const combined = records;
  const jsonPath = path.join(DATA_DIR, "json", `${register}.json`);
  if (fs.existsSync(jsonPath)) {
    const jsonRows = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
    combined.push(...jsonRows.map((row) => Object.fromEntries(headers.map((h) => [h, row[h] ?? ""]))));
  }
  combined.push(...parseXmlRecords(path.join(DATA_DIR, "xml", `${register}.xml`)).map((row) => Object.fromEntries(headers.map((h) => [h, row[h] ?? ""]))));
  return { headers, records: combined };
}

function peselChecksum(firstTen) {
  const weights = [1, 3, 7, 9, 1, 3, 7, 9, 1, 3];
  const sum = firstTen.split("").reduce((acc, digit, i) => acc + Number(digit) * weights[i], 0);
  return String((10 - (sum % 10)) % 10);
}

function makePesel(index, female) {
  const year = 1960 + (index % 46);
  const month = 1 + (index % 12);
  const day = 1 + (index % 28);
  return makePeselFromDate(`${pad(year, 4)}-${pad(month, 2)}-${pad(day, 2)}`, female, index);
}

function makePeselFromDate(dateValue, female, index) {
  const match = String(dateValue ?? "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return makePesel(index, female);
  const year = Number(match[1]);
  let month = Number(match[2]);
  const day = Number(match[3]);
  if (year >= 1800 && year <= 1899) month += 80;
  else if (year >= 2000 && year <= 2099) month += 20;
  else if (year >= 2100 && year <= 2199) month += 40;
  else if (year >= 2200 && year <= 2299) month += 60;
  const serial = pad((index * 137) % 10000, 4);
  const genderDigit = female ? Number(serial[3]) - (Number(serial[3]) % 2) : Number(serial[3]) | 1;
  const firstTen = `${pad(year % 100, 2)}${pad(month, 2)}${pad(day, 2)}${serial.slice(0, 3)}${genderDigit}`;
  return `${firstTen}${peselChecksum(firstTen)}`;
}

function weightedNumber(index, length, weights) {
  let base = pad((index * 7919 + 123456789).toString(), length - 1).slice(-(length - 1));
  const sum = base.split("").reduce((acc, digit, i) => acc + Number(digit) * weights[i], 0);
  let check = sum % 11;
  if (check === 10) return weightedNumber(index + 1, length, weights);
  return `${base}${check}`;
}

function makeNip(index) {
  return weightedNumber(index, 10, [6, 5, 7, 2, 3, 4, 5, 6, 7]);
}

function makeRegon(index) {
  return weightedNumber(index, 9, [8, 9, 2, 3, 4, 5, 6, 7]);
}

function mod97(value) {
  let remainder = 0;
  for (const digit of String(value)) {
    remainder = (remainder * 10 + Number(digit)) % 97;
  }
  return remainder;
}

function leiToDigits(value) {
  return String(value).toUpperCase().replace(/[0-9A-Z]/g, (char) => (
    /[A-Z]/.test(char) ? String(char.charCodeAt(0) - 55) : char
  ));
}

function makeLei(index) {
  const chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  let entity = "";
  for (let i = 0; i < 14; i += 1) {
    entity += chars[(index * (i + 7) + i * 11 + 17) % chars.length];
  }
  const base = `5299${entity}`;
  const check = 98 - mod97(`${leiToDigits(base)}00`);
  return `${base}${pad(check, 2)}`;
}

function makeIdCard(index) {
  const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  const a = letters[(index * 3) % 26];
  const b = letters[(index * 5 + 7) % 26];
  const c = letters[(index * 11 + 13) % 26];
  const tail = pad((index * 76543) % 100000, 5);
  const values = [a, b, c].map((ch) => ch.charCodeAt(0) - 55);
  const tailDigits = tail.split("").map(Number);
  const withoutCheck = values[0] * 7 + values[1] * 3 + values[2] * 1
    + tailDigits.reduce((acc, digit, i) => acc + digit * [7, 3, 1, 7, 3][i], 0);
  const check = withoutCheck % 10;
  return `${a}${b}${c}${check}${tail}`;
}

function breakDigit(value) {
  const text = String(value ?? "");
  const i = [...text].findIndex((ch) => /\d/.test(ch));
  if (i < 0) return `${text}X`;
  return `${text.slice(0, i)}${(Number(text[i]) + 1) % 10}${text.slice(i + 1)}`;
}

function breakEmail(value, variant) {
  const text = String(value ?? "");
  if (variant % 2 === 0 && text.includes("@")) {
    return text.replace("@", "");
  }

  const atIndex = text.indexOf("@");
  const dotIndex = text.indexOf(".", atIndex >= 0 ? atIndex : 0);
  if (dotIndex >= 0) {
    return `${text.slice(0, dotIndex)}${text.slice(dotIndex + 1)}`;
  }

  return text.includes("@") ? text.replace("@", "") : `${text}.invalid`;
}

function typo(value) {
  const chars = [...String(value ?? "")];
  const letters = chars.map((ch, i) => [ch, i]).filter(([ch]) => /\p{L}/u.test(ch));
  if (letters.length < 3) return value;
  const [, pos] = letters[Math.floor(rand() * letters.length)];
  if (pos + 1 < chars.length && /\p{L}/u.test(chars[pos + 1])) {
    [chars[pos], chars[pos + 1]] = [chars[pos + 1], chars[pos]];
  } else {
    chars.splice(pos, 1);
  }
  return chars.join("");
}

function removePolishDiacritic(value) {
  const replacements = {
    "ą": "a",
    "ć": "c",
    "ę": "e",
    "ł": "l",
    "ń": "n",
    "ó": "o",
    "ś": "s",
    "ź": "z",
    "ż": "z",
    "Ą": "A",
    "Ć": "C",
    "Ę": "E",
    "Ł": "L",
    "Ń": "N",
    "Ó": "O",
    "Ś": "S",
    "Ź": "Z",
    "Ż": "Z",
  };
  const chars = [...String(value ?? "")];
  const index = chars.findIndex((ch) => replacements[ch]);
  if (index < 0) return value;
  chars[index] = replacements[chars[index]];
  return chars.join("");
}

function addressParts(index, invalid = false) {
  const [province, district, municipality, localityUpper, city, street, postalCode] = pick(ADDRESSES, index);
  const building = 1 + ((index * 17) % 180);
  const apartment = index % 4 === 0 ? `/${1 + ((index * 13) % 90)}` : "";
  if (invalid) {
    return {
      province: "NIEZNANE",
      district: "NIEISTNIEJĄCY",
      municipality: "NIEISTNIEJĄCA",
      localityUpper: "NIBYLANDIA",
      city: "Nibylandia",
      street: "Nieistniejąca",
      postalCode: "99-999",
      building,
      apartment,
    };
  }
  return { province, district, municipality, localityUpper, city, street, postalCode, building, apartment };
}

function setAddress(record, headers, index, options = {}) {
  const p = addressParts(index, options.invalid);
  const streetPrefix = pick(STREET_PREFIXES, index);
  const isEstate = index % 29 === 0;
  const streetName = isEstate ? `os. ${p.street}` : p.street;
  const houseNumberOnly = !options.invalid && HOUSE_NUMBER_ONLY_CITIES.has(p.city) && index % 7 === 0;
  const streetLine = options.missingStreet
    ? ""
    : houseNumberOnly
      ? `${p.building}${p.apartment}`
      : [isEstate ? "" : streetPrefix, streetName, `${p.building}${p.apartment}`].filter(Boolean).join(" ");
  const locationLine = [
    options.missingPostal ? "" : p.postalCode,
    options.missingCity ? "" : p.city,
  ].filter(Boolean).join(" ");
  const full = [streetLine, locationLine].filter(Boolean).join(", ");
  for (const key of headers) {
    const compact = keyId(key);
    if (options.missingCity && (compact === "miejscowosc" || compact === "siedziba")) {
      record[key] = "";
      continue;
    }
    if (compact === "wojewodztwo") record[key] = p.province;
    else if (compact === "powiat") record[key] = p.district;
    else if (compact === "gmina") record[key] = p.municipality;
    else if (compact === "miejscowosc" || compact === "miejscowość") record[key] = key === "Miejscowość" ? p.city : p.localityUpper;
    else if (compact === "siedziba") record[key] = p.city;
    else if (compact.includes("kodpocztowy")) record[key] = options.missingPostal ? "" : p.postalCode;
    else if (key === "Ulica i numer") record[key] = streetLine;
    else if (compact.includes("adres") || compact.includes("address")) record[key] = full;
  }
}

function normalizeIdentifiers(record, headers, index) {
  const female = String(record.Plec || "").toUpperCase() === "K" || isFemaleIndex(index);
  for (const key of headers) {
    const compact = keyId(key);
    if (compact.includes("pesel")) record[key] = makePeselFromDate(record.DataUrodzenia, female, index + key.length);
    else if (compact.includes("lei")) record[key] = makeLei(index + key.length);
    else if (compact.endsWith("nip") || compact.includes("numernip")) record[key] = makeNip(index + key.length);
    else if (compact.endsWith("regon")) record[key] = makeRegon(index + key.length);
    else if (compact.includes("krs")) record[key] = pad((index * 97 + key.length) % 10000000000, 10);
    else if (compact.includes("dowoduosobistego") || compact.includes("idcard")) record[key] = index % 8 === 0 ? "" : makeIdCard(index + key.length);
  }
}

function normalizeNames(record, headers, index) {
  const personCache = new Map();
  const companyBase = pick(COMPANY_BASE, index);
  const company = `${companyBase} ${pick(COMPANY_SUFFIXES, index)}`;
  const getPerson = (key) => {
    const prefix = keyId(key).replace(/(drugieimie|imie|nazwisko)$/, "");
    if (!personCache.has(prefix)) {
      const female = isFemaleIndex(index);
      personCache.set(prefix, personFor(index + prefix.length, female));
    }
    return personCache.get(prefix);
  };

  for (const key of headers) {
    const compact = keyId(key);
    if (compact === "plec") {
      record[key] = isFemaleIndex(index) ? "K" : "M";
    }
  }

  for (const key of headers) {
    const compact = keyId(key);
    const person = getPerson(key);
    if (compact === "imieojca") record[key] = pick(MALE_FIRST_NAMES, index + 3);
    else if (compact === "imiematki") record[key] = pick(FEMALE_FIRST_NAMES, index + 7);
    else if (compact === "drugieimie" || compact.endsWith("drugieimie")) record[key] = person.second;
    else if (compact === "imie" || compact.endsWith("imie")) record[key] = person.first;
    else if (compact === "nazwiskorodowe" || compact.endsWith("nazwiskorodowe")) record[key] = familyNameFor(index, isFemaleIndex(index));
    else if (compact === "nazwisko" || compact.endsWith("nazwisko")) record[key] = person.last;
    else if (compact === "name" || compact === "nazwa" || compact.includes("firmanazwa")) record[key] = company;
    else if (compact.includes("nazwaskrocona") || compact.includes("skroconanazwa")) record[key] = companyBase;
    else if (compact === "formaprawna" || compact === "entitylegalformcode" || compact === "legalentitytype") record[key] = pick(LEGAL_FORM_VARIANTS, index);
    else if (compact === "email" || compact.includes("email")) {
      const emailPerson = personCache.get("firmawlasciciel") || personCache.get("") || personFor(index, isFemaleIndex(index));
      const hasPersonalColumns = headers.some((header) => {
        const id = keyId(header);
        return id === "imie" || id.endsWith("imie") || id === "nazwisko" || id.endsWith("nazwisko") || id.includes("wlasciciel");
      });
      record[key] = hasPersonalColumns ? emailForPerson(index, companyBase, emailPerson) : emailForCompany(index, companyBase);
    }
    else if (compact === "stronawww" || compact === "www" || compact.endsWith("www") || compact.includes("website") || compact.includes("url")) record[key] = index % 6 === 0 ? "" : websiteFor(index, companyBase);
  }

  normalizeIdentifiers(record, headers, index);
}

function cloneRecord(base, headers, index) {
  const record = Object.fromEntries(headers.map((h) => [h, base[h] ?? ""]));
  normalizeNames(record, headers, index);
  setAddress(record, headers, index);
  for (const key of headers) {
    if (/id$/i.test(key) || key === "firma.id") record[key] = `${key.replace(/[^A-Za-z0-9]/g, "").toUpperCase()}-${pad(index + 1, 5)}`;
    if (key === "Numer agenta") record[key] = `${pad(10000000 + index, 8)}/A/${pad(300000 + index, 6)}`;
  }
  return record;
}

function selectIndexes(count, howMany, offset) {
  const step = Math.max(1, Math.floor(count / howMany));
  const result = [];
  for (let i = 0; result.length < howMany && i < count * 2; i += 1) {
    const candidate = (offset + i * step) % count;
    if (!result.includes(candidate)) result.push(candidate);
  }
  return result;
}

function applyAnomalies(records, headers) {
  const total = records.length;
  const typoIndexes = selectIndexes(total, Math.round(total * 0.02), 7);
  const missingDiacriticIndexes = selectIndexes(total, Math.round(total * 0.01), 13);
  const incompleteRecordIndexes = selectIndexes(total, Math.round(total * 0.0075), 17);
  const missingPostal = selectIndexes(total, Math.round(total * 0.01), 19);
  const missingStreet = selectIndexes(total, Math.round(total * 0.01), 37);
  const invalidAddress = selectIndexes(total, Math.round(total * 0.0075), 53);
  const missingCity = selectIndexes(total, Math.round(total * 0.01), 83);
  const missingPostalAndCity = selectIndexes(total, Math.round(total * 0.005), 101);
  const missingBirthDate = selectIndexes(total, Math.round(total * 0.005), 61);
  for (const i of missingPostal) setAddress(records[i], headers, i, { missingPostal: true });
  for (const i of missingStreet) setAddress(records[i], headers, i, { missingStreet: true });
  for (const i of invalidAddress) setAddress(records[i], headers, i, { invalid: true });
  for (const i of missingCity) setAddress(records[i], headers, i, { missingCity: true });
  for (const i of missingPostalAndCity) setAddress(records[i], headers, i, { missingPostal: true, missingCity: true });
  for (const i of missingBirthDate) {
    for (const field of headers) {
      if (keyId(field) === "dataurodzenia") records[i][field] = "";
    }
  }

  const optionalKrsFields = ["nazwaskrocona", "formaprawna", "pkd", "kapitalzakladowy", "reprezentacja", "datarejestracji", "status"];
  if (headers.some((field) => keyId(field) === "numerkrs")) {
    const missingKrsOptional = [
      [selectIndexes(total, Math.round(total * 0.015), 113), "nazwaskrocona"],
      [selectIndexes(total, Math.round(total * 0.01), 127), "formaprawna"],
      [selectIndexes(total, Math.round(total * 0.01), 139), "pkd"],
      [selectIndexes(total, Math.round(total * 0.01), 151), "kapitalzakladowy"],
      [selectIndexes(total, Math.round(total * 0.01), 163), "reprezentacja"],
      [selectIndexes(total, Math.round(total * 0.005), 179), "datarejestracji"],
      [selectIndexes(total, Math.round(total * 0.005), 191), "status"],
    ];
    for (const [indexes, fieldId] of missingKrsOptional) {
      for (const rowIndex of indexes) {
        for (const field of headers) {
          if (keyId(field) === fieldId && optionalKrsFields.includes(fieldId)) records[rowIndex][field] = "";
        }
      }
    }
  }

  const typoFields = headers.filter((h) => {
    const id = keyId(h);
    return !/(pesel|nip|regon|krs|lei|dowod|data|date|email|telefon|phone|kod|adres|address|www|url|plec|obywatelstwo|imieojca|imiematki)/.test(id);
  });
  for (const i of typoIndexes) {
    const candidates = typoFields.filter((h) => String(records[i][h] ?? "").length > 4);
    if (candidates.length) {
      const key = candidates[Math.floor(rand() * candidates.length)];
      records[i][key] = typo(records[i][key]);
    }
  }
  for (const i of missingDiacriticIndexes) {
    const candidates = typoFields.filter((h) => /[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]/.test(String(records[i][h] ?? "")));
    if (candidates.length) {
      const key = candidates[Math.floor(rand() * candidates.length)];
      records[i][key] = removePolishDiacritic(records[i][key]);
    }
  }

  const nullableFields = headers;
  for (const i of incompleteRecordIndexes) {
    const candidates = nullableFields.filter((h) => String(records[i][h] ?? "").trim() !== "");
    if (candidates.length) {
      const key = candidates[Math.floor(rand() * candidates.length)];
      records[i][key] = "";
    }
  }

  const emailFields = headers.filter((h) => keyId(h).includes("email"));
  const emailRefs = [];
  for (let rowIndex = 0; rowIndex < records.length; rowIndex += 1) {
    for (const field of emailFields) {
      if (records[rowIndex][field]) emailRefs.push([rowIndex, field]);
    }
  }
  const badEmailCount = Math.round(emailRefs.length * 0.01);
  const badEmailIndexes = selectIndexes(emailRefs.length, badEmailCount, 131);
  for (let i = 0; i < badEmailIndexes.length; i += 1) {
    const [rowIndex, field] = emailRefs[badEmailIndexes[i]];
    records[rowIndex][field] = breakEmail(records[rowIndex][field], i);
  }

  const idGroups = {
    pesel: headers.filter((h) => keyId(h).includes("pesel")),
    lei: headers.filter((h) => keyId(h).includes("lei")),
    nip: headers.filter((h) => keyId(h).includes("nip")),
    regon: headers.filter((h) => keyId(h).includes("regon")),
    idCard: headers.filter((h) => /(dowoduosobistego|idcard)/.test(keyId(h))),
  };
  const offsets = { pesel: 59, lei: 67, nip: 71, regon: 89, idCard: 107 };
  for (const [type, fields] of Object.entries(idGroups)) {
    const refs = [];
    for (let rowIndex = 0; rowIndex < records.length; rowIndex += 1) {
      for (const field of fields) {
        if (records[rowIndex][field]) refs.push([rowIndex, field]);
      }
    }
    if (!refs.length) continue;

    const badCount = Math.max(1, Math.round(refs.length * 0.01));
    const missingCount = type === "pesel" || type === "lei" ? 0 : Math.round(refs.length * 0.005);
    const badIndexes = new Set(selectIndexes(refs.length, badCount, offsets[type]));
    const missingIndexes = selectIndexes(refs.length, missingCount, offsets[type] + 17)
      .filter((idx) => !badIndexes.has(idx));

    for (const refIndex of badIndexes) {
      const [rowIndex, field] = refs[refIndex];
      records[rowIndex][field] = breakDigit(records[rowIndex][field]);
    }
    for (const refIndex of missingIndexes) {
      const [rowIndex, field] = refs[refIndex];
      records[rowIndex][field] = "";
    }
  }
}

function jsonRecords(headers, records) {
  return records.map((record) => Object.fromEntries(headers.map((h) => [h, record[h] === "" ? null : record[h]])));
}

function writeXml(register, headers, records) {
  const body = records.map((record) => {
    const fields = headers.map((h) => `    <field name="${xmlEscape(h)}">${xmlEscape(record[h] ?? "")}</field>`).join("\n");
    return `  <record>\n${fields}\n  </record>`;
  }).join("\n");
  fs.writeFileSync(path.join(DATA_DIR, "xml", `${register}.xml`), `<?xml version="1.0" encoding="UTF-8"?>\n<dataset name="${xmlEscape(register)}">\n${body}\n</dataset>\n`, "utf8");
}

function colRef(index) {
  let n = index + 1;
  let s = "";
  while (n > 0) {
    const r = (n - 1) % 26;
    s = String.fromCharCode(65 + r) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

const CRC_TABLE = Array.from({ length: 256 }, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) crc = CRC_TABLE[(crc ^ byte) & 0xff] ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
}

function dosDateTime(date = new Date("2026-05-07T12:00:00Z")) {
  const time = (date.getHours() << 11) | (date.getMinutes() << 5) | Math.floor(date.getSeconds() / 2);
  const dosDate = ((date.getFullYear() - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate();
  return { time, date: dosDate };
}

function listFiles(dir, root = dir) {
  const files = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) files.push(...listFiles(full, root));
    else files.push({ abs: full, name: path.relative(root, full).replace(/\\/g, "/") });
  }
  return files;
}

function writeZip(sourceDir, outPath) {
  const chunks = [];
  const central = [];
  let offset = 0;
  const { time, date } = dosDateTime();

  for (const file of listFiles(sourceDir)) {
    const nameBuffer = Buffer.from(file.name, "utf8");
    const data = fs.readFileSync(file.abs);
    const crc = crc32(data);
    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4);
    local.writeUInt16LE(0x0800, 6);
    local.writeUInt16LE(0, 8);
    local.writeUInt16LE(time, 10);
    local.writeUInt16LE(date, 12);
    local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(data.length, 18);
    local.writeUInt32LE(data.length, 22);
    local.writeUInt16LE(nameBuffer.length, 26);
    local.writeUInt16LE(0, 28);
    chunks.push(local, nameBuffer, data);

    const c = Buffer.alloc(46);
    c.writeUInt32LE(0x02014b50, 0);
    c.writeUInt16LE(20, 4);
    c.writeUInt16LE(20, 6);
    c.writeUInt16LE(0x0800, 8);
    c.writeUInt16LE(0, 10);
    c.writeUInt16LE(time, 12);
    c.writeUInt16LE(date, 14);
    c.writeUInt32LE(crc, 16);
    c.writeUInt32LE(data.length, 20);
    c.writeUInt32LE(data.length, 24);
    c.writeUInt16LE(nameBuffer.length, 28);
    c.writeUInt16LE(0, 30);
    c.writeUInt16LE(0, 32);
    c.writeUInt16LE(0, 34);
    c.writeUInt16LE(0, 36);
    c.writeUInt32LE(0, 38);
    c.writeUInt32LE(offset, 42);
    central.push(c, nameBuffer);
    offset += local.length + nameBuffer.length + data.length;
  }

  const centralOffset = offset;
  const centralSize = central.reduce((sum, chunk) => sum + chunk.length, 0);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(0, 4);
  end.writeUInt16LE(0, 6);
  end.writeUInt16LE(central.length / 2, 8);
  end.writeUInt16LE(central.length / 2, 10);
  end.writeUInt32LE(centralSize, 12);
  end.writeUInt32LE(centralOffset, 16);
  end.writeUInt16LE(0, 20);
  fs.writeFileSync(outPath, Buffer.concat([...chunks, ...central, end]));
}

function writeXlsx(register, headers, records) {
  const tmp = path.join(DATA_DIR, ".xlsx-tmp", register);
  fs.rmSync(tmp, { recursive: true, force: true });
  fs.mkdirSync(path.join(tmp, "_rels"), { recursive: true });
  fs.mkdirSync(path.join(tmp, "docProps"), { recursive: true });
  fs.mkdirSync(path.join(tmp, "xl", "_rels"), { recursive: true });
  fs.mkdirSync(path.join(tmp, "xl", "worksheets"), { recursive: true });
  fs.mkdirSync(path.join(tmp, "xl", "styles"), { recursive: true });

  const rows = [headers, ...records.map((r) => headers.map((h) => r[h] ?? ""))].map((values, rowIndex) => {
    const cells = values.map((value, colIndex) => `<c r="${colRef(colIndex)}${rowIndex + 1}" t="inlineStr"><is><t>${xmlEscape(value)}</t></is></c>`).join("");
    return `<row r="${rowIndex + 1}">${cells}</row>`;
  }).join("");

  fs.writeFileSync(path.join(tmp, "[Content_Types].xml"), '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>', "utf8");
  fs.writeFileSync(path.join(tmp, "_rels", ".rels"), '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>', "utf8");
  fs.writeFileSync(path.join(tmp, "docProps", "core.xml"), '<?xml version="1.0" encoding="UTF-8"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:creator>synthetic-data-generator</dc:creator></cp:coreProperties>', "utf8");
  fs.writeFileSync(path.join(tmp, "docProps", "app.xml"), '<?xml version="1.0" encoding="UTF-8"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>Goldenizacja</Application></Properties>', "utf8");
  fs.writeFileSync(path.join(tmp, "xl", "workbook.xml"), '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="data" sheetId="1" r:id="rId1"/></sheets></workbook>', "utf8");
  fs.writeFileSync(path.join(tmp, "xl", "_rels", "workbook.xml.rels"), '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles/styles.xml"/></Relationships>', "utf8");
  fs.writeFileSync(path.join(tmp, "xl", "styles", "styles.xml"), '<?xml version="1.0" encoding="UTF-8"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="1"><font/></fonts><fills count="1"><fill/></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="1"><xf xfId="0"/></cellXfs></styleSheet>', "utf8");
  fs.writeFileSync(path.join(tmp, "xl", "worksheets", "sheet1.xml"), `<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>${rows}</sheetData></worksheet>`, "utf8");

  const out = path.join(DATA_DIR, "xlsx", `${register}.xlsx`);
  fs.rmSync(out, { force: true });
  writeZip(tmp, out);
}

function writeRegister(register, headers, records) {
  const splits = {
    csv: records.slice(0, TARGET_PER_FORMAT),
    json: records.slice(TARGET_PER_FORMAT, TARGET_PER_FORMAT * 2),
    xml: records.slice(TARGET_PER_FORMAT * 2, TARGET_PER_FORMAT * 3),
    xlsx: records.slice(TARGET_PER_FORMAT * 3, TARGET_PER_FORMAT * 4),
  };
  fs.writeFileSync(path.join(DATA_DIR, "csv", `${register}.csv`), stringifyCsv(headers, splits.csv), "utf8");
  fs.writeFileSync(path.join(DATA_DIR, "json", `${register}.json`), `${JSON.stringify(jsonRecords(headers, splits.json), null, 2)}\n`, "utf8");
  writeXml(register, headers, splits.xml);
  writeXlsx(register, headers, splits.xlsx);
  return Object.fromEntries(FORMATS.map((format) => [format, splits[format].length]));
}

function main() {
  const registers = fs.readdirSync(path.join(DATA_DIR, "csv"))
    .filter((name) => name.endsWith(".csv"))
    .map((name) => path.basename(name, ".csv"))
    .sort();
  const manifest = Object.fromEntries(FORMATS.map((format) => [format, {}]));
  for (const register of registers) {
    const { headers, records: sourceRecords } = readRecords(register);
    const records = [];
    for (let i = 0; i < TARGET_PER_REGISTER; i += 1) {
      records.push(cloneRecord(sourceRecords[i % sourceRecords.length], headers, i));
    }
    applyAnomalies(records, headers);
    const counts = writeRegister(register, headers, records);
    for (const format of FORMATS) manifest[format][register] = counts[format];
    console.log(`${register}: ${records.length} records`);
  }
  fs.rmSync(path.join(DATA_DIR, ".xlsx-tmp"), { recursive: true, force: true });
  fs.writeFileSync(path.join(DATA_DIR, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
}

main();
