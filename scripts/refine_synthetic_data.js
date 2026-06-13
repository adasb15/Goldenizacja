const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const DATA_DIR = path.join(ROOT, "data");
const FORMATS = ["csv", "json", "xml", "xlsx"];
const TARGET_PER_REGISTER = 800;
const TARGET_PER_FORMAT = TARGET_PER_REGISTER / FORMATS.length;
const DUPLICATED_PERSONS_PER_FORMAT = 0;
const HARD_PERSON_CONFLICT_RATE = 0.005;
const RNG_SEED = 20260507;
const KRS_ROLE_SLOT_CAP = 4;
const PERSON_IDENTITY_SEED_MULTIPLIER = 1000;
const RELATED_COMPANY_SEED_OFFSET = 1000000;

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
  ["LUBUSKIE", "WARSZAWSKI", "ŻARY", "ŻARY", "Żary", "Rynek", "68-200"], // Poprawiony błędny powiat
  ["LUBUSKIE", "\u015aWIEBODZI\u0143SKI", "\u015aWIEBODZIN", "\u015aWIEBODZIN", "\u015awiebodzin", "Sikorskiego", "66-200"],
  ["ZACHODNIOPOMORSKIE", "KO\u0141OBRZESKI", "KO\u0141OBRZEG", "KO\u0141OBRZEG", "Ko\u0142obrzeg", "Armii Krajowej", "78-100"],
  ["ZACHODNIOPOMORSKIE", "STARGARDZKI", "STARGARD", "STARGARD", "Stargard", "Pi\u0142sudskiego", "73-110"],
  ["\u015aWI\u0118TOKRZYSKIE", "SANDOMIERSKI", "SANDOMIERZ", "SANDOMIERZ", "Sandomierz", "Mickiewicza", "27-600"],
  ["\u015aWI\u0118TOKRZYSKIE", "OSTROWIECKI", "OSTROWIEC \u015aWI\u0118TOKRZYSKI", "OSTROWIEC \u015aWI\u0118TOKRZYSKI", "Ostrowiec \u015awi\u0119tokrzyski", "Sienkiewicza", "27-400"],
];

const EXTRA_ADDRESSES = [
  ["MAZOWIECKIE", "WARSZAWA", "WARSZAWA", "WARSZAWA", "Warszawa", "Chmielna", "00-020"],
  ["MAZOWIECKIE", "WARSZAWA", "WARSZAWA", "WARSZAWA", "Warszawa", "Nowy Świat", "00-029"],
  ["MAZOWIECKIE", "WARSZAWA", "WARSZAWA", "WARSZAWA", "Warszawa", "os. Przyjaźń", "01-355"],
  ["MAZOWIECKIE", "LEGIONOWSKI", "LEGIONOWO", "LEGIONOWO", "Legionowo", "Jagiellońska", "05-120"],
  ["MAZOWIECKIE", "WOŁOMIŃSKI", "MARKI", "MARKI", "Marki", "Piłsudskiego", "05-270"],
  ["MAZOWIECKIE", "OTWOCKI", "OTWOCK", "OTWOCK", "Otwock", "Andriollego", "05-400"],
  ["MAZOWIECKIE", "RADOM", "RADOM", "RADOM", "Radom", "Żeromskiego", "26-600"],
  ["MAZOWIECKIE", "PŁOCK", "PŁOCK", "PŁOCK", "Płock", "Tumska", "09-402"],
  ["MAŁOPOLSKIE", "KRAKÓW", "KRAKÓW", "KRAKÓW", "Kraków", "Karmelicka", "31-128"],
  ["MAŁOPOLSKIE", "KRAKÓW", "KRAKÓW", "KRAKÓW", "Kraków", "os. Na Stoku", "31-704"],
  ["MAŁOPOLSKIE", "TATRZAŃSKI", "ZAKOPANE", "ZAKOPANE", "Zakopane", "Krupówki", "34-500"],
  ["MAŁOPOLSKIE", "LIMANOWSKI", "LIMANOWA", "MORDARKA", "Mordarka", "", "34-600"],
  ["MAŁOPOLSKIE", "KRAKOWSKI", "ZIELONKI", "ZIELONKI", "Zielonki", "Galicyjska", "32-087"],
  ["MAŁOPOLSKIE", "WIELICKI", "NIEPOŁOMICE", "PODŁĘŻE", "Podłęże", "", "32-003"],
  ["MAŁOPOLSKIE", "TARNÓW", "TARNÓW", "TARNÓW", "Tarnów", "Wałowa", "33-100"],
  ["ŁÓDZKIE", "ŁÓDŹ", "ŁÓDŹ", "ŁÓDŹ", "Łódź", "Narutowicza", "90-135"],
  ["ŁÓDZKIE", "ŁÓDŹ", "ŁÓDŹ", "ŁÓDŹ", "Łódź", "os. Retkinia", "94-004"],
  ["ŁÓDZKIE", "PABIANICKI", "PABIANICE", "PABIANICE", "Pabianice", "Zamkowa", "95-200"],
  ["ŁÓDZKIE", "ZGIERZ", "ZGIERZ", "ZGIERZ", "Zgierz", "Długa", "95-100"],
  ["DOLNOŚLĄSKIE", "WROCŁAW", "WROCŁAW", "WROCŁAW", "Wrocław", "Rynek", "50-101"],
  ["DOLNOŚLĄSKIE", "WROCŁAW", "WROCŁAW", "WROCŁAW", "Wrocław", "Jedności Narodowej", "50-260"],
  ["DOLNOŚLĄSKIE", "JELENIOGÓRSKI", "KARPACZ", "KARPACZ", "Karpacz", "Konstytucji 3 Maja", "58-540"],
  ["DOLNOŚLĄSKIE", "LUBIŃSKI", "LUBIN", "LUBIN", "Lubin", "Odrodzenia", "59-300"],
  ["DOLNOŚLĄSKIE", "WAŁBRZYCH", "WAŁBRZYCH", "WAŁBRZYCH", "Wałbrzych", "Słowackiego", "58-300"],
  ["WIELKOPOLSKIE", "POZNAŃ", "POZNAŃ", "POZNAŃ", "Poznań", "Półwiejska", "61-888"],
  ["WIELKOPOLSKIE", "POZNAŃ", "POZNAŃ", "POZNAŃ", "Poznań", "os. Bolesława Chrobrego", "60-681"],
  ["WIELKOPOLSKIE", "KALISZ", "KALISZ", "KALISZ", "Kalisz", "Główny Rynek", "62-800"],
  ["WIELKOPOLSKIE", "OSTROWSKI", "OSTRÓW WIELKOPOLSKI", "OSTRÓW WIELKOPOLSKI", "Ostrów Wielkopolski", "Kaliska", "63-400"],
  ["POMORSKIE", "GDAŃSK", "GDAŃSK", "GDAŃSK", "Gdańsk", "Ogarna", "80-826"],
  ["POMORSKIE", "GDAŃSK", "GDAŃSK", "GDAŃSK", "Gdańsk", "os. Jasień", "80-180"],
  ["POMORSKIE", "SOPOT", "SOPOT", "SOPOT", "Sopot", "Bohaterów Monte Cassino", "81-759"],
  ["POMORSKIE", "KARTUSKI", "ŻUKOWO", "CHWASZCZYNO", "Chwaszczyno", "", "80-209"],
  ["ŚLĄSKIE", "KATOWICE", "KATOWICE", "KATOWICE", "Katowice", "3 Maja", "40-096"],
  ["ŚLĄSKIE", "KATOWICE", "KATOWICE", "KATOWICE", "Katowice", "os. Paderewskiego", "40-282"],
  ["ŚLĄSKIE", "GLIWICE", "GLIWICE", "GLIWICE", "Gliwice", "Zwycięstwa", "44-100"],
  ["ŚLĄSKIE", "TYCHY", "TYCHY", "TYCHY", "Tychy", "Bocheńskiego", "43-100"],
  ["ŚLĄSKIE", "CZĘSTOCHOWA", "CZĘSTOCHOWA", "CZĘSTOCHOWA", "Częstochowa", "Najświętszej Maryi Panny", "42-200"],
  ["ŚLĄSKIE", "BIELSKO-BIAŁA", "BIELSKO-BIAŁA", "BIELSKO-BIAŁA", "Bielsko-Biała", "11 Listopada", "43-300"],
  ["PODKARPACKIE", "RZESZOWSKI", "BOGUCHWAŁA", "NIECHOBRZ", "Niechobrz", "", "36-047"],
  ["PODKARPACKIE", "PRZEMYŚL", "PRZEMYŚL", "PRZEMYŚL", "Przemyśl", "Franciszkańska", "37-700"],
  ["PODKARPACKIE", "SANOCKI", "SANOK", "SANOK", "Sanok", "Kościuszki", "38-500"],
  ["PODLASKIE", "BIAŁYSTOK", "BIAŁYSTOK", "BIAŁYSTOK", "Białystok", "Suraska", "15-422"],
  ["PODLASKIE", "BIAŁOSTOCKI", "SUPRAŚL", "OGRODNICZKI", "Ogrodniczki", "", "16-030"],
  ["PODLASKIE", "HAJNOWSKI", "HAJNÓWKA", "HAJNÓWKA", "Hajnówka", "3 Maja", "17-200"],
  ["LUBELSKIE", "LUBLIN", "LUBLIN", "LUBLIN", "Lublin", "os. LSM", "20-400"],
  ["LUBELSKIE", "KAZIMIERSKI", "KAZIMIERZ DOLNY", "MIĘĆMIERZ", "Mięćmierz", "", "24-120"],
  ["LUBELSKIE", "BIALSKI", "BIAŁA PODLASKA", "BIAŁA PODLASKA", "Biała Podlaska", "Brzeska", "21-500"],
  ["KUJAWSKO-POMORSKIE", "TORUŃ", "TORUŃ", "TORUŃ", "Toruń", "Rynek Staromiejski", "87-100"],
  ["KUJAWSKO-POMORSKIE", "BYDGOSZCZ", "BYDGOSZCZ", "BYDGOSZCZ", "Bydgoszcz", "Mostowa", "85-110"],
  ["WARMIŃSKO-MAZURSKIE", "OLSZTYN", "OLSZTYN", "OLSZTYN", "Olsztyn", "Stare Miasto", "10-026"],
  ["WARMIŃSKO-MAZURSKIE", "MRĄGOWSKI", "MRĄGOWO", "MRĄGOWO", "Mrągowo", "Warszawska", "11-700"],
  ["ZACHODNIOPOMORSKIE", "SZCZECIN", "SZCZECIN", "SZCZECIN", "Szczecin", "Wojska Polskiego", "70-470"],
  ["ZACHODNIOPOMORSKIE", "ŚWINOUJŚCIE", "ŚWINOUJŚCIE", "ŚWINOUJŚCIE", "Świnoujście", "Monte Cassino", "72-600"],
  ["OPOLSKIE", "OPOLE", "OPOLE", "OPOLE", "Opole", "Rynek", "45-015"],
  ["OPOLSKIE", "KLUCZBORSKI", "KLUCZBORK", "KLUCZBORK", "Kluczbork", "Byczyńska", "46-200"],
  ["LUBUSKIE", "GORZÓW WIELKOPOLSKI", "GORZÓW WIELKOPOLSKI", "GORZÓW WIELKOPOLSKI", "Gorzów Wielkopolski", "Chrobrego", "66-400"],
  ["LUBUSKIE", "MIĘDZYRZECKI", "MIĘDZYRZECZ", "MIĘDZYRZECZ", "Międzyrzecz", "30 Stycznia", "66-300"],
  ["ŚWIĘTOKRZYSKIE", "KIELCE", "KIELCE", "KIELCE", "Kielce", "Paderewskiego", "25-004"],
  ["ŚWIĘTOKRZYSKIE", "BUSKI", "BUSKO-ZDRÓJ", "BUSKO-ZDRÓJ", "Busko-Zdrój", "1 Maja", "28-100"],
];

const ADDRESS_POOL = ADDRESSES.concat(EXTRA_ADDRESSES);

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
  "Mordarka",
  "Podłęże",
  "Chwaszczyno",
  "Niechobrz",
  "Ogrodniczki",
  "Mięćmierz",
  "Tarnów"
]);


const FEMALE_FIRST_NAMES = [
  "Anna", "Maria", "Katarzyna", "Joanna", "Ewa", "Magdalena", "Monika", "Agnieszka", "Barbara", "Justyna",
  "Aleksandra", "Natalia", "Marta", "Karolina", "Paulina", "Małgorzata", "Elżbieta", "Teresa", "Dorota", "Iwona",
  "Beata", "Renata", "Urszula", "Alicja", "Izabela", "Patrycja", "Weronika", "Wiktoria", "Zofia", "Julia",
  "Olga", "Kinga", "Ewelina", "Kamila", "Sylwia", "Halina", "Grażyna", "Danuta", "Bożena", "Aneta",
  "Zuzanna", "Maja", "Lena", "Oliwia", "Hanna", "Emilia", "Amelia", "Gabriela", "Martyna", "Dominika",
  "Agata", "Jagoda", "Helena", "Krystyna", "Jadwiga", "Irena", "Monika", "Izabela", "Sabina", "Mirosława"
];

const MALE_FIRST_NAMES = [
  "Piotr", "Tomasz", "Michał", "Krzysztof", "Paweł", "Adam", "Robert", "Marek", "Wojciech", "Rafał",
  "Jan", "Andrzej", "Marcin", "Łukasz", "Grzegorz", "Mateusz", "Jakub", "Dawid", "Artur", "Dariusz",
  "Sebastian", "Sławomir", "Maciej", "Mariusz", "Zbigniew", "Henryk", "Ryszard", "Stanisław", "Jacek", "Bartłomiej",
  "Przemysław", "Damian", "Kamil", "Bartosz", "Daniel", "Leszek", "Waldemar", "Cezary", "Norbert", "Filip",
  "Kacper", "Mikołaj", "Szymon", "Antoni", "Aleksander", "Franciszek", "Ignacy", "Nikodem", "Leon", "Miłosz",
  "Maciej", "Tadeusz", "Jerzy", "Stefan", "Marian", "Józef", "Władysław", "Edward", "Mirosław", "Arkadiusz"
];

const FEMALE_FIRST_NAME_SET = new Set(FEMALE_FIRST_NAMES.map((name) => transliteratePolish(name).toLowerCase()));
const MALE_FIRST_NAME_SET = new Set(MALE_FIRST_NAMES.map((name) => transliteratePolish(name).toLowerCase()));

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
  ["Sawicka", "Sawicki"],
  ["Dudek", "Dudek"],
  ["Adamczyk", "Adamczyk"],
  ["Pawłowska", "Pawłowski"],
  ["Nowicka", "Nowicki"],
  ["Sokołowska", "Sokołowski"],
  ["Wróbel", "Wróbel"],
  ["Majewska", "Majewski"],
  ["Olszewska", "Olszewski"],
  ["Jaworska", "Jaworski"],
  ["Malinowska", "Malinowski"],
  ["Pająk", "Pająk"],
  ["Szczepańska", "Szczepański"],
  ["Czerwińska", "Czerwiński"],
  ["Kubiak", "Kubiak"],
  ["Wilk", "Wilk"],
  ["Wysocka", "Wysocki"],
  ["Chmielewska", "Chmielewski"],
  ["Urbańska", "Urbański"],
  ["Błaszczyk", "Błaszczyk"],
  ["Szulc", "Szulc"],
  ["Kozak", "Kozak"],
  ["Cieślak", "Cieślak"],
  ["Andrzejewska", "Andrzejewski"],
  ["Gajewska", "Gajewski"],
  ["Laskowska", "Laskowski"],
  ["Mazurek", "Mazurek"],
  ["Sobczak", "Sobczak"],
  ["Konieczna", "Konieczny"],
  ["Brzezińska", "Brzeziński"],
  ["Makowska", "Makowski"],
  ["Wrona", "Wrona"],
  ["Bąk", "Bąk"],
  ["Kucharska", "Kucharski"],
  ["Lisowska", "Lisowski"],
  ["Słowik", "Słowik"],
  ["Kopeć", "Kopeć"],
  ["Czajka", "Czajka"],
  ["Matusiak", "Matusiak"],
  ["Gajda", "Gajda"],
  ["Klimek", "Klimek"],
  ["Madej", "Madej"],
  ["Krupa", "Krupa"],
  ["Kaczmarczyk", "Kaczmarczyk"],
  ["Wrona", "Wrona"],
  ["Wasilewska", "Wasilewski"],
  ["Kalinowska", "Kalinowski"],
  ["Zarychta", "Zarychta"],
  ["Przybylska", "Przybylski"],
  ["Michalak", "Michalak"],
  ["Szatkowska", "Szatkowski"],
  ["Bednarek", "Bednarek"],
  ["Podgórska", "Podgórski"],
  ["Śliwińska", "Śliwiński"],
  ["Czajkowska", "Czajkowski"],
  ["Biernat", "Biernat"],
  ["Panek", "Panek"],
  ["Prus", "Prus"],
  ["Janik", "Janik"]
];

const COMPANY_TRADE_NAMES = [
  "Facebook - Meta",
  "Google - Alphabet",
  "Instagram - Meta",
  "Allegro Lokalnie",
  "mBank",
  "Orlen Paczka",
  "X - Twitter",
  "Booking.com",
];
const COMPANY_PREFIXES = [
  "PPHU",
  "P.P.H.U.",
];
const GLEIF_REGISTERED_AT_KRS = "National Court Register (Ministry of Justice) | Krajowy Rejestr Sadowy (KRS) (Ministerstwo Sprawiedliwosci) | Poland | RA000466";
const GLEIF_REGISTERED_AT_REGON = "National Official Business Register (Central Statistical Office) | Krajowy Rejestr Urzedowy Podmiotow Gospodarki Narodowej REGON (Glowny Urzad Statystyczny) | Poland | RA000484";
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
const LIMITED_LIABILITY_LEGAL_FORM_VARIANTS = [
  "sp\u00f3\u0142ka z ograniczon\u0105 odpowiedzialno\u015bci\u0105",
  "sp. z o.o.",
  "sp z oo",
  "SP Z O O",
];
const JOINT_STOCK_LEGAL_FORM_VARIANTS = [
  "sp\u00f3\u0142ka akcyjna",
  "S.A.",
  "SA",
];
const STREET_PREFIXES = ["ul.", "ul", "ulica", ""];
const MAIL_DOMAINS = [
  "gmail.com",
  "outlook.com",
  "wp.pl",
  "onet.pl",
  "interia.pl",
  "o2.pl",
  "proton.me",
  "yahoo.com",
];
const PERSON_MAIL_DOMAINS = MAIL_DOMAINS;
const MISSING_EMAIL_DOMAINS = [
  "abxza.pl",
  "uuu.xs",
  "pocztaa.pl",
  "gmai1.com",
  "onett.pl",
  "biuuro.pl",
  "firmaa.pl",
  "mail.xz",
  "kontaktqq.pl",
  "protonn.me",
  "finanse24.xs",
  "ubezpiecznia.pl",
];
const WEB_TLDS = [".pl", ".com.pl", ".eu", ".local"];

function generateHighlyDiverseCompanyPool() {
  const NOUNS = [
    "Amber", "Bizon", "Canyon", "Delfin", "Echo", "Falcon", "Gryf", "Horyzont", "Ikar", "Jantar",
    "Koral", "Lotos", "Magnolia", "Neon", "Oaza", "Pegaz", "Rubin", "Szafir", "Tytan", "Uran",
    "Wektor", "Zefir", "Żubr", "Sokół", "Orzeł", "Kormoran", "Barycz", "Noteć", "Pilica", "Narew",
    "Jodełka", "Kaktus", "Szmaragd", "Topaz", "Granit", "Marmur", "Syrena", "Zodiak", "Olimp", "Zorza",
    "Krokus", "Narcyz", "Giewont", "Rysy", "Kasprowy", "Beskid", "Bieszczady", "Karpaty", "Bałtyk", "Sudety"
  ];

  const ADJECTIVES = [
    "Zielony", "Niebieski", "Złoty", "Srebrny", "Czysty", "Szybki", "Pewny", "Dobry", "Polski", "Europejski",
    "Globalny", "Lokalny", "Nowoczesny", "Tradycyjny", "Dynamiczny", "Stabilny", "Innowacyjny", "Kreatywny", "Aktywny", "Jasny",
    "Green", "Blue", "Gold", "Silver", "Smart", "Fast", "Safe", "Best", "Global", "Future",
    "Wielkopolski", "Śląski", "Mazowiecki", "Pomorski", "Dolnośląski", "Karpacki", "Bałtycki", "Młody", "Wspólny", "Pierwszy"
  ];

  const INDUSTRIES = [
    "Budownictwo", "Transport", "Spedycja", "Logistyka", "Handel", "Usługi", "Finanse", "Doradztwo", "Szkolenia", "Media",
    "Reklama", "Marketing", "Druk", "Informatyka", "Oprogramowanie", "Rolnictwo", "Ogrodnictwo", "Produkcja", "Przemysł", "Ekologia",
    "Energetyka", "Instalacje", "Nieruchomości", "Inwestycje", "Medycyna", "Zdrowie", "Urody", "Turystyka", "Rozrywka", "Gastronomia",
    "Moda", "Tekstylia", "Motoryzacja", "Ubezpieczenia", "Spawalnictwo", "Ślusarstwo", "Krawiectwo", "Ochrona", "Catering", "Księgowość"
  ];

  const NAMES = ["Kowalski", "Nowak", "Wiśniewski", "Wójcik", "Kowalczyk", "Kamiński", "Zieliński", "Szymański", "Woźniak", "Kozłowski"];

  const ABSTRACT_BUSINESS = [
    "Astra", "Apex", "Clarity", "Core", "Direct", "Envio", "Focus", "Genesis", "Impact", "Krypton",
    "Logos", "Matrix", "Nexum", "Omni", "Pulse", "Quest", "Radius", "Summit", "Target", "Vertex",
    "Alpina", "Arteria", "Consilio", "Dignitas", "Exact", "Fortis", "Idea", "Linear", "Meritum", "Optima",
    "Profis", "Rationo", "Signum", "Talent", "Unia", "Valor", "Vera", "Zenith", "Avangarda", "Inwencja"
  ];

  const SEED_NAMES = [
    "Krajowy Rejestr Długów", "Polskie Przetwory", "Hurtownia Nabiału Mleczko", "Agencja Reklamowa Kreatywni",
    "Kancelaria Prawna Sankcja", "Śląskie Zakłady Mechaniczne", "Fabryka Okien i Drzwi Profil",
    "Przedsiębiorstwo Robót Drogowych", "Krakowskie Biuro Nieruchomości", "Salon Samochodowy Auto-Hit",
    "Klinika Stomatologiczna Dent-Med", "Polski Tytoń", "Gdańska Stocznia Jachtowa", "Wytwórnia Makaronu Jajecznego",
    "Zakłady Mięsne Tradycja", "Spółdzielnia Mleczarska Radomsko", "Kancelaria Finansowo-Księgowa Bilans",
    "Zarząd Nieruchomości Komercyjnych", "Polskie Linie Oceaniczne", "Hurtownia Materiałów Budowlanych Cegiełka",
    "Studio Projektowe Architektura", "Centrum Medycyny Pracy", "Przedsiębiorstwo Energetyki Cieplnej",
    "Gospodarstwo Rolno-Ogrodnicze", "Drukarnia Wielkoformatowa Impress", "Klub Fitness Sylwetka",
    "Polska Grupa Energetyczna", "Mazowieckie Zakłady Drobiarskie", "Hurtownia Farmaceutyczna Aptekarz",
    "Kancelaria Notarialna Lex", "Biuro Podróży Wojażer", "Szkoła Języków Obcych Lingua",
    "Centrum Logistyczne Podlasie", "Fabryka Mebli Drewnianych Dąb", "Polskie Sady",
    "Wielkopolska Hurtownia Stali", "Zakład Oczyszczania Miasta", "Przedsiębiorstwo Wodociągów i Kanalizacji",
    "Instytut Badań Rynkowych", "Agencja Ochrony Solidna", "Salon Meblowy Komfort",
    "Krajowa Izba Gospodarcza", "Polskie Zakłady Lotnicze", "Hurtownia Elektryczna Wat",
    "Centrum Ogrodnicze Zielona Oaza", "Piekarnia i Cukiernia Chrupiący Rogalik",
    "Zakład Usług Komunalnych", "Polski Komfort", "Kancelaria Radców Prawnych Partnerzy",
    "Centrum Dystrybucji Alkoholi", "Przedsiębiorstwo Spedycyjne Ładunek", "Fabryka Tekstyliów Splot",
    "Górnośląskie Towarzystwo Finansowe", "Krajowa Agencja Informacyjna", "Polskie Jagody"
  ];

  const pool = [];
  const seen = new Set();
  const addToPool = (value) => {
    if (!seen.has(value)) {
      seen.add(value);
      pool.push(value);
    }
  };

  for (const value of SEED_NAMES) addToPool(value);

  for (let round = 0; pool.length < 150 && round < NOUNS.length; round += 1) {
    for (let i = 0; i < ADJECTIVES.length && pool.length < 150; i += 1) {
      const nounIndex = (i * 7 + round * 11) % NOUNS.length;
      addToPool(`${ADJECTIVES[i]} ${NOUNS[nounIndex]}`);
    }
  }

  for (let round = 0; pool.length < 270 && round < NOUNS.length; round += 1) {
    for (let j = 0; j < INDUSTRIES.length && pool.length < 270; j += 1) {
      const nounIndex = (j * 5 + round * 9) % NOUNS.length;
      addToPool(`${NOUNS[nounIndex]} ${INDUSTRIES[j]}`);
    }
  }

  const SUFFIX_WORDS = ["Group", "Systems", "Holding", "Partners", "Polska", "Enterprise", "Network"];
  for (let i = 0; i < ABSTRACT_BUSINESS.length; i++) {
    for (let j = 0; j < SUFFIX_WORDS.length; j++) {
      if (pool.length >= 380) break;
      addToPool(`${ABSTRACT_BUSINESS[i]} ${SUFFIX_WORDS[j]}`);
    }
  }

  const FAMILY_SUFFIX = ["i Synowie", "i Wspólnicy", "Spółka Rodzinna", "Bracia"];
  for (let i = 0; i < NAMES.length; i++) {
    for (let j = 0; j < FAMILY_SUFFIX.length; j++) {
      addToPool(`${NAMES[i]} ${FAMILY_SUFFIX[j]}`);
    }
  }

  for (let i = 0; i < INDUSTRIES.length; i++) {
    const adj = ADJECTIVES[(i * 3) % ADJECTIVES.length];
    addToPool(`${INDUSTRIES[i]} ${adj}`);
  }

  const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  while (pool.length < 530) {
    let acro = LETTERS[Math.floor(Math.random() * 26)] + 
               LETTERS[Math.floor(Math.random() * 26)] + 
               LETTERS[Math.floor(Math.random() * 26)];
    addToPool(acro);
  }

  return pool.slice(0, 500);
}

const COMPANY_BASE = generateHighlyDiverseCompanyPool();

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

function formatSliceIndex(index) {
  return index % TARGET_PER_FORMAT;
}

function personSeedFor(index) {
  return index;
}

function companySeedFor(index) {
  return index;
}

function isDuplicatedPersonIndex(index) {
  return DUPLICATED_PERSONS_PER_FORMAT > 0 && formatSliceIndex(index) < DUPLICATED_PERSONS_PER_FORMAT;
}

function duplicateVariantIndex(index) {
  return Math.floor(index / TARGET_PER_FORMAT);
}

function makeSharedKrs(index) {
  return pad((companySeedFor(index) * 97 + "numerKRS".length) % 10000000000, 10);
}

function makeSharedNip(index) {
  return makeNip(companySeedFor(index) + "nip".length);
}

function makeSharedRegon(index) {
  return makeRegon(companySeedFor(index) + "regon".length);
}

function hasDoubleBarrelLastName(index, female) {
  return female && index % 40 === 0;
}

function hasDoubleBarrelFamilyName(index) {
  const targetInHundred = Math.floor(index / 100) % 2 === 0 ? 50 : 51;
  return index % 100 === targetInHundred;
}

function personFor(index, female, doubleBarrelIndex = index) {
  const firstNames = female ? FEMALE_FIRST_NAMES : MALE_FIRST_NAMES;
  const lastPair = pick(LAST_NAME_PAIRS, index);
  const doubleBarrelLastName = hasDoubleBarrelLastName(doubleBarrelIndex, female);
  const secondLastPair = pick(LAST_NAME_PAIRS, index + 11);
  const lastName = female ? lastPair[0] : lastPair[1];
  const secondLastName = female ? secondLastPair[0] : secondLastPair[1];
  return {
    first: pick(firstNames, index),
    second: index % 3 === 0 ? "" : pick(firstNames, index + 5),
    last: doubleBarrelLastName ? `${lastName}-${secondLastName}` : lastName,
    lastParts: doubleBarrelLastName ? [lastName, secondLastName] : [lastName],
  };
}

function familyNameFor(index, female, person = null) {
  if (female && person?.lastParts?.length > 1) {
    return person.lastParts[(index / 40) % 2 === 0 ? 0 : 1];
  }
  if (hasDoubleBarrelFamilyName(index)) {
    const firstPair = pick(LAST_NAME_PAIRS, index + 9);
    const secondPair = pick(LAST_NAME_PAIRS, index + 17);
    const first = female ? firstPair[0] : firstPair[1];
    const second = female ? secondPair[0] : secondPair[1];
    return `${first}-${second}`;
  }
  if (female && index % 3 !== 0) return pick(LAST_NAME_PAIRS, index + 9)[0];
  if (!female && index % 8 === 0) return pick(LAST_NAME_PAIRS, index + 9)[1];
  return "";
}

function firstNameGender(value) {
  const normalized = transliteratePolish(String(value ?? "").trim()).toLowerCase();
  if (FEMALE_FIRST_NAME_SET.has(normalized)) return "female";
  if (MALE_FIRST_NAME_SET.has(normalized)) return "male";
  return "";
}

function secondNameForGender(value, index, female) {
  const normalized = String(value ?? "").trim();
  if (!normalized) return "";
  const gender = firstNameGender(normalized);
  if ((female && gender === "female") || (!female && gender === "male")) return normalized;
  return pick(female ? FEMALE_FIRST_NAMES : MALE_FIRST_NAMES, index + 5);
}

function personFieldPrefix(compactKey) {
  if (compactKey.startsWith("drugieimie")) return compactKey.slice("drugieimie".length);
  if (compactKey.startsWith("secondname")) return compactKey.slice("secondname".length);
  if (compactKey.startsWith("middlename")) return compactKey.slice("middlename".length);
  if (compactKey.startsWith("imie")) return compactKey.slice("imie".length);
  if (compactKey.startsWith("nazwisko")) return compactKey.slice("nazwisko".length);
  return compactKey.replace(/(drugieimie|secondname|middlename|imie|nazwisko)$/, "");
}

function stableHash(value) {
  let hash = 0;
  for (const ch of String(value ?? "")) {
    hash = ((hash * 31) + ch.charCodeAt(0)) >>> 0;
  }
  return hash;
}

function personIdentityPrefix(compactKey) {
  return String(compactKey)
    .replace(/(drugieimie|secondname|middlename|imie|nazwiskorodowe|nazwisko|pesel|plec|dataurodzenia|miejsceurodzenia|obywatelstwo|numerdowoduosobistego|idcard|numerpaszportu|passport)$/, "");
}

function personIdentitySeed(seed, compactKey = "") {
  const baseSeed = personSeedFor(seed);
  const prefix = personIdentityPrefix(compactKey);
  if (!prefix || prefix === "firmawlasciciel" || prefix === "ofwca") return baseSeed;
  return (baseSeed * PERSON_IDENTITY_SEED_MULTIPLIER) + 1000 + (stableHash(prefix) % PERSON_IDENTITY_SEED_MULTIPLIER);
}

function relatedCompanySeed(seed, slot) {
  return RELATED_COMPANY_SEED_OFFSET + (companySeedFor(seed) * 100) + slot;
}

function krsRoleConfigs() {
  return [
    { countField: "LiczbaCzlonekZarzadu", prefix: "CzlonekZarzadu", maxSlots: 10 },
    { countField: "LiczbaProkurent", prefix: "Prokurent", maxSlots: 10 },
    { countField: "LiczbaWspolnikOsoba", prefix: "WspolnikOsoba", maxSlots: 10 },
    { countField: "LiczbaLikwidator", prefix: "Likwidator", maxSlots: 10 },
    { countField: "LiczbaCzlonekRadyNadzorczej", prefix: "CzlonekRadyNadzorczej", maxSlots: 10 },
    { countField: "LiczbaWspolnikPodmiot", prefix: "WspolnikPodmiot", maxSlots: 10 },
  ];
}

function parseNonNegativeInt(value, fallback = 0) {
  const parsed = Number.parseInt(String(value ?? "").trim(), 10);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
}

function clearKrsRoleSlot(record, headers, prefix, slot) {
  const marker = `${prefix}${slot}_`;
  for (const header of headers) {
    if (String(header).startsWith(marker)) {
      record[header] = "";
    }
  }
}

function enforceKrsRoleCardinality(record, headers) {
  for (const { countField, prefix, maxSlots } of krsRoleConfigs()) {
    if (!headers.includes(countField)) continue;
    const declaredCount = parseNonNegativeInt(record[countField], 0);
    const effectiveCount = Math.min(declaredCount, KRS_ROLE_SLOT_CAP);
    record[countField] = String(effectiveCount);
    for (let slot = effectiveCount + 1; slot <= maxSlots; slot += 1) {
      clearKrsRoleSlot(record, headers, prefix, slot);
    }
  }
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
    .replace(/-spolka-z-ograniczona-odpowiedzialnoscia|-sp-z-o-o|-sp-z-oo|-sa|-s-a|-spolka-akcyjna|-pphu|-p-p-h-u/g, "")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

function companyInfoFor(index) {
  const base = pick(COMPANY_BASE, index);
  if (index % 20 === 0) {
    const exceptionIndex = Math.floor(index / 20);
    if (exceptionIndex % 2 === 0) {
      const tradeName = pick(COMPANY_TRADE_NAMES, exceptionIndex);
      return { base: tradeName, full: tradeName, short: tradeName, legalForm: "" };
    }

    const prefix = exceptionIndex % 4 === 1 ? "PPHU" : "P.P.H.U.";
    const full = `${prefix} ${base}`;
    return { base, full, short: full, legalForm: "" };
  }

  const suffix = pick(COMPANY_SUFFIXES, index);
  const full = `${base} ${suffix}`;
  const legalFormVariants = suffix.toLowerCase().includes("akcyjna") || /\bs\.?\s*a\.?\b/i.test(suffix)
    ? JOINT_STOCK_LEGAL_FORM_VARIANTS
    : LIMITED_LIABILITY_LEGAL_FORM_VARIANTS;
  return {
    base,
    full,
    short: base,
    legalForm: pick(legalFormVariants, index),
  };
}

function emailForPerson(index, companyBase, person) {
  const domain = pick(PERSON_MAIL_DOMAINS, index);
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
  const domain = pick(MAIL_DOMAINS, index);
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
  const parsed = parseCsv(fs.readFileSync(csvPath, "utf8"));
  const headers = withRegisterSpecificHeaders(
    register,
    register === "gleif" ? withGleifRegistrationHeaders(parsed.headers) : parsed.headers,
  );
  const records = parsed.records.map((row) => Object.fromEntries(headers.map((h) => [h, row[h] ?? ""])));
  const combined = records;
  const jsonPath = path.join(DATA_DIR, "json", `${register}.json`);
  if (fs.existsSync(jsonPath)) {
    const jsonRows = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
    combined.push(...jsonRows.map((row) => Object.fromEntries(headers.map((h) => [h, row[h] ?? ""]))));
  }
  combined.push(...parseXmlRecords(path.join(DATA_DIR, "xml", `${register}.xml`)).map((row) => Object.fromEntries(headers.map((h) => [h, row[h] ?? ""]))));
  return { headers, records: combined };
}

function withRegisterSpecificHeaders(register, headers) {
  let result = [...headers];
  if (register === "krs") {
    result = withKrsSecondNameHeaders(result);
  }
  if (
    register === "knf_rejestr_posrednikow_ubezpieczeniowych_agent"
    || register === "knf_rejestr_posrednikow_ubezpieczeniowych_pracownik_agenta"
  ) {
    result = withColumnAfter(result, "Imię", "DrugieImię");
  }
  if (register === "knf_rejestr_firm_inwestycyjnych") {
    result = withColumnAfter(result, "CzlonekZarzadu1_Imie", "CzlonekZarzadu1_DrugieImie");
  }
  return result;
}

function withKrsSecondNameHeaders(headers) {
  let result = [...headers];
  const rolePrefixes = [
    "CzlonekZarzadu",
    "Prokurent",
    "WspolnikOsoba",
    "Likwidator",
    "CzlonekRadyNadzorczej",
  ];
  for (const prefix of rolePrefixes) {
    for (let slot = 1; slot <= 10; slot += 1) {
      result = withColumnAfter(
        result,
        `${prefix}${slot}_Imie`,
        `${prefix}${slot}_DrugieImie`,
      );
    }
  }
  return result;
}

function withColumnAfter(headers, anchor, column) {
  if (headers.includes(column)) return headers;
  const anchorIndex = headers.indexOf(anchor);
  if (anchorIndex < 0) return headers;
  const result = [...headers];
  result.splice(anchorIndex + 1, 0, column);
  return result;
}

function withGleifRegistrationHeaders(headers) {
  const result = headers.filter((header) => header !== "ValidationAuthorityID" && header !== "ValidationAuthorityEntityID");
  const insertAfter = result.indexOf("ValidationSources");
  if (!result.includes("RegisteredAt")) {
    result.splice(insertAfter >= 0 ? insertAfter + 1 : result.length, 0, "RegisteredAt");
  }
  if (!result.includes("RegisteredAs")) {
    const registeredAtIndex = result.indexOf("RegisteredAt");
    result.splice(registeredAtIndex >= 0 ? registeredAtIndex + 1 : result.length, 0, "RegisteredAs");
  }
  return result;
}

function parseDateParts(value) {
  const rawText = String(value ?? "").trim();
  const text = rawText.includes("T") ? rawText.split("T", 1)[0] : rawText.split(" ", 1)[0];
  let match = text.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (match) {
    const iso = { year: Number(match[1]), month: Number(match[2]), day: Number(match[3]) };
    if (isValidDateParts(iso)) return iso;
    return { year: Number(match[1]), month: Number(match[3]), day: Number(match[2]) };
  }

  match = text.match(/^(\d{2})-(\d{2})-(\d{4})$/);
  if (match) return { year: Number(match[3]), month: Number(match[2]), day: Number(match[1]) };

  match = text.match(/^(\d{4})\/(\d{2})\/(\d{2})$/);
  if (match) return { year: Number(match[1]), month: Number(match[3]), day: Number(match[2]) };

  match = text.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (match) return { year: Number(match[3]), month: Number(match[2]), day: Number(match[1]) };

  match = text.match(/^(\d{8})(\d{4}|\d{6})?$/);
  if (match) return { year: Number(text.slice(0, 4)), month: Number(text.slice(4, 6)), day: Number(text.slice(6, 8)) };

  return null;
}

function parseGeneratedDateParts(value) {
  const rawText = String(value ?? "").trim();
  const text = rawText.includes("T") ? rawText.split("T", 1)[0] : rawText.split(" ", 1)[0];

  let match = text.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (match && !rawText.includes("T")) {
    return { year: Number(match[1]), month: Number(match[3]), day: Number(match[2]) };
  }

  match = text.match(/^(\d{4})\/(\d{2})\/(\d{2})$/);
  if (match) return { year: Number(match[1]), month: Number(match[3]), day: Number(match[2]) };

  return parseDateParts(value);
}

function isValidDateParts(parts) {
  if (!parts) return false;
  const date = new Date(Date.UTC(parts.year, parts.month - 1, parts.day));
  return date.getUTCFullYear() === parts.year
    && date.getUTCMonth() === parts.month - 1
    && date.getUTCDate() === parts.day;
}

function formatDateVariant(parts, index, key) {
  const year = pad(parts.year, 4);
  const month = pad(parts.month, 2);
  const day = pad(parts.day, 2);
  const hour = pad((index + key.length) % 24, 2);
  const minute = pad((index * 7 + key.length) % 60, 2);
  const second = pad((index * 11 + key.length) % 60, 2);
  const variantSeed = index + key.length;
  const variant = variantSeed % 97 === 0 ? 5 + ((index + key.length * 3) % 5) : variantSeed % 5;
  switch (variant) {
    case 0:
      return `${day}/${month}/${year}`;
    case 1:
      return `${year}/${day}/${month}`;
    case 2:
      return `${day}-${month}-${year}`;
    case 3:
      return `${year}-${day}-${month}`;
    case 5:
      return `${year}-${month}-${day}T${hour}:${minute}:${second}Z`;
    case 6:
      return `${year}-${day}-${month} ${hour}:${minute}`;
    case 7:
      return `${day}/${month}/${year} ${hour}:${minute}`;
    case 8:
      return `${day}-${month}-${year} ${hour}:${minute}:${second}`;
    case 9:
      return `${year}${month}${day}${hour}${minute}`;
    default:
      return `${year}${month}${day}`;
  }
}

function dateFromIndex(index, key) {
  const year = keyId(key) === "dataurodzenia" ? 1960 + (index % 46) : 2015 + (index % 12);
  const month = 1 + ((index + key.length) % 12);
  const day = 1 + ((index * 7 + key.length) % 28);
  return { year, month, day };
}

function datePartsToUtc(parts) {
  if (!isValidDateParts(parts)) return null;
  return Date.UTC(parts.year, parts.month - 1, parts.day);
}

function addDays(parts, days) {
  const date = new Date(Date.UTC(parts.year, parts.month - 1, parts.day + days));
  return {
    year: date.getUTCFullYear(),
    month: date.getUTCMonth() + 1,
    day: date.getUTCDate(),
  };
}

function dateRole(compactKey) {
  if (
    compactKey.includes("wykresl")
    || compactKey.includes("wyrejest")
    || compactKey.includes("deregistration")
    || compactKey.includes("termination")
    || compactKey.includes("validto")
    || compactKey.endsWith("datado")
  ) {
    return "end";
  }
  if (compactKey.includes("wznow")) return "resume";
  if (compactKey.includes("zawies")) return "suspension";
  if (
    compactKey.includes("wpis")
    || compactKey.includes("rejestr")
    || compactKey.includes("powstania")
    || compactKey.includes("rozpoczecia")
    || compactKey.includes("registrationlegaldate")
    || compactKey.includes("initialregistrationdate")
    || compactKey.includes("validfrom")
    || compactKey.endsWith("dataod")
  ) {
    return "start";
  }
  if (compactKey.includes("decyzji") || compactKey.includes("decision")) return "decision";
  return "";
}

function enforceDateChronology(record, headers, index) {
  const dateFields = headers
    .map((key) => {
      const compact = keyId(key);
      if (!/(data|date|validfrom|validto)/.test(compact)) return null;
      const parts = parseGeneratedDateParts(record[key]);
      if (!isValidDateParts(parts)) return null;
      return { key, compact, role: dateRole(compact), parts };
    })
    .filter(Boolean);

  const starts = dateFields.filter((field) => field.role === "start");
  const ends = dateFields.filter((field) => field.role === "end");
  const suspensions = dateFields.filter((field) => field.role === "suspension");
  const resumes = dateFields.filter((field) => field.role === "resume");
  const decisions = dateFields.filter((field) => field.role === "decision");

  const baseline = starts[0]?.parts ?? decisions[0]?.parts ?? dateFromIndex(index, "DataWpisu");
  const startByCompact = new Map(starts.map((field) => [field.compact, field.parts]));
  const pairedStartFor = (field) => {
    if (field.compact.endsWith("datado")) {
      return startByCompact.get(`${field.compact.slice(0, -"datado".length)}dataod`);
    }
    if (field.compact.endsWith("validto")) {
      return startByCompact.get(`${field.compact.slice(0, -"validto".length)}validfrom`);
    }
    return null;
  };

  for (const field of starts) {
    if (datePartsToUtc(field.parts) > datePartsToUtc(baseline)) {
      field.parts = baseline;
      record[field.key] = formatDateVariant(field.parts, index, field.key);
    }
  }

  for (const field of decisions) {
    if (starts.length && datePartsToUtc(field.parts) > datePartsToUtc(baseline)) {
      field.parts = addDays(baseline, -30);
      record[field.key] = formatDateVariant(field.parts, index, field.key);
    }
  }

  for (const field of suspensions) {
    if (datePartsToUtc(field.parts) <= datePartsToUtc(baseline)) {
      field.parts = addDays(baseline, 180);
      record[field.key] = formatDateVariant(field.parts, index, field.key);
    }
  }

  for (const field of resumes) {
    const suspension = suspensions[0]?.parts ?? baseline;
    if (datePartsToUtc(field.parts) <= datePartsToUtc(suspension)) {
      field.parts = addDays(suspension, 60);
      record[field.key] = formatDateVariant(field.parts, index, field.key);
    }
  }

  for (const field of ends) {
    const minimum = pairedStartFor(field) ?? resumes[0]?.parts ?? suspensions[0]?.parts ?? baseline;
    if (datePartsToUtc(field.parts) <= datePartsToUtc(minimum)) {
      field.parts = addDays(minimum, 365);
      record[field.key] = formatDateVariant(field.parts, index, field.key);
    }
  }
}

function isCompanyEstablishmentDate(compactKey) {
  return [
    "datarejestracji",
    "datapowstania",
    "registrationlegaldate",
    "initialregistrationdate",
    "firmadatarozpoczeciadzialalnosci",
  ].includes(compactKey);
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

function makePeselFromDate(dateValue, female, index, generatedFormat = false) {
  const parts = generatedFormat ? parseGeneratedDateParts(dateValue) : parseDateParts(dateValue);
  if (!isValidDateParts(parts)) return makePesel(index, female);
  const year = parts.year;
  let month = parts.month;
  const day = parts.day;
  if (year >= 1800 && year <= 1899) month += 80;
  else if (year >= 2000 && year <= 2099) month += 20;
  else if (year >= 2100 && year <= 2199) month += 40;
  else if (year >= 2200 && year <= 2299) month += 60;
  const serial = pad((index * 137) % 10000, 4);
  const genderDigit = female ? Number(serial[3]) - (Number(serial[3]) % 2) : Number(serial[3]) | 1;
  const firstTen = `${pad(year % 100, 2)}${pad(month, 2)}${pad(day, 2)}${serial.slice(0, 3)}${genderDigit}`;
  return `${firstTen}${peselChecksum(firstTen)}`;
}

function makeSharedPesel(index, female) {
  const seed = personSeedFor(index);
  const parts = dateFromIndex(seed, "DataUrodzenia");
  const dateValue = `${pad(parts.year, 4)}-${pad(parts.month, 2)}-${pad(parts.day, 2)}`;
  return makePeselFromDate(dateValue, female, seed + "PESEL".length);
}

function weightedNumber(index, length, weights) {
  const modulus = 10 ** (length - 1);
  let candidate = Math.abs((Number(index) || 0) * 7919 + 123456789);
  for (let attempt = 0; attempt < 1000; attempt += 1) {
    const base = pad(String(candidate % modulus), length - 1);
    const sum = base.split("").reduce((acc, digit, i) => acc + Number(digit) * weights[i], 0);
    const check = sum % 11;
    if (check !== 10) return `${base}${check}`;
    candidate += 1000003;
  }
  throw new Error(`Cannot generate weighted number for index ${index}`);
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
  const entity = String(Math.abs(Number(index) || 0)).padStart(14, "0").slice(-14);
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

function makePassport(index) {
  const prefixes = ["PA", "PB", "PC", "PL", "PX"];
  return `${pick(prefixes, index)}${pad((index * 3571 + 246813) % 10000000, 7)}`;
}

function breakDigit(value) {
  const text = String(value ?? "");
  const i = [...text].findIndex((ch) => /\d/.test(ch));
  if (i < 0) return `${text}X`;
  return `${text.slice(0, i)}${(Number(text[i]) + 1) % 10}${text.slice(i + 1)}`;
}

function breakKrsFormat(value) {
  const text = String(value ?? "");
  if (text.length > 0) return text.slice(0, -1);
  return "KRS-BAD";
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

function replaceEmailDomainWithMissing(value, index) {
  const text = String(value ?? "");
  const atIndex = text.lastIndexOf("@");
  if (atIndex < 0) return text;

  const localPart = text.slice(0, atIndex);
  return `${localPart}@${pick(MISSING_EMAIL_DOMAINS, index)}`;
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

function duplicatedPersonTextVariant(value, index, fieldId) {
  if (!isDuplicatedPersonIndex(index)) return value;
  const variant = duplicateVariantIndex(index);
  if (variant === 0 || value === null || value === undefined || value === "") return value;

  const text = String(value);
  if (fieldId.includes("imie") && variant === 1) return typo(text);
  if (fieldId.includes("nazwisko") && variant === 2) return typo(text);
  if (fieldId.includes("adres") && variant === 3) return text.replace(/\bul\.?\s*/i, "ulica ");
  return text;
}


function addressParts(index, invalid = false) {
  const [province, district, municipality, localityUpper, city, street, postalCode] = pick(ADDRESS_POOL, index);
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
  const ruralHouseNumberOnly = !p.street;
  const houseNumberOnly = !options.invalid && (ruralHouseNumberOnly || (HOUSE_NUMBER_ONLY_CITIES.has(p.city) && index % 7 === 0));
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
    else if (compact.includes("kodpocztowy") || compact === "postalcode") record[key] = options.missingPostal ? "" : p.postalCode;
    else if (compact === "country" || compact === "legaljurisdiction") record[key] = "PL";
    else if (key === "Ulica i numer") record[key] = streetLine;
    else if (compact.includes("adres") || compact.includes("address")) record[key] = full;
  }
}

function normalizeDates(record, headers, index, seed = index, register = "") {
  for (const key of headers) {
    const compact = keyId(key);
    if (!/(^data|data$|date)/.test(compact)) continue;

    const value = String(record[key] ?? "").trim();
    if (!value) continue;
    const parsed = parseDateParts(value);
    const parts = register !== "pesel" && isCompanyEstablishmentDate(compact)
      ? dateFromIndex(seed, "Establishment_Date")
      : register === "pesel" && compact === "dataurodzenia"
      ? dateFromIndex(seed, key)
      : isValidDateParts(parsed) ? parsed : dateFromIndex(seed, key);
    record[key] = formatDateVariant(parts, index, key);
  }
}

function normalizeIdentifiers(record, headers, index, seed = index) {
  for (const key of headers) {
    const compact = keyId(key);
    const identitySeed = personIdentitySeed(seed, compact);
    const fieldFemale = String(record.Plec || "").toUpperCase() === "K" && personIdentityPrefix(compact) === ""
      ? true
      : isFemaleIndex(identitySeed);
    const relatedPartyMatch = String(key).match(/^WspolnikPodmiot(\d+)_(KRS|NIP)$/i);
    if (relatedPartyMatch) {
      const relatedSeed = relatedCompanySeed(seed, Number(relatedPartyMatch[1]));
      record[key] = relatedPartyMatch[2].toUpperCase() === "KRS" ? makeSharedKrs(relatedSeed) : makeSharedNip(relatedSeed);
      continue;
    }

    if (compact.includes("pesel")) record[key] = record.DataUrodzenia && personIdentityPrefix(compact) === ""
      ? makePeselFromDate(record.DataUrodzenia, fieldFemale, identitySeed + "PESEL".length, true)
      : makeSharedPesel(identitySeed, fieldFemale);
    else if (compact === "directparentlei") record[key] = makeLei(companySeedFor(seed) + 100000);
    else if (compact === "ultimateparentlei") record[key] = makeLei(companySeedFor(seed) + 200000);
    else if (compact.includes("lei")) record[key] = makeLei(companySeedFor(seed));
    else if (compact === "registrationauthorityid" || compact === "registeredat") {
      record[key] = companySeedFor(seed) % 2 === 0 ? "RA000466" : "RA000484";
      if (compact === "registeredat") {
        record[key] = companySeedFor(seed) % 2 === 0 ? GLEIF_REGISTERED_AT_KRS : GLEIF_REGISTERED_AT_REGON;
      }
    }
    else if (compact === "registrationauthorityentityid" || compact === "registeredas") {
      record[key] = companySeedFor(seed) % 2 === 0 ? makeSharedKrs(seed) : makeSharedRegon(seed);
    }
    else if (compact.endsWith("nip") || compact.includes("numernip")) record[key] = makeSharedNip(seed);
    else if (compact.endsWith("regon")) record[key] = makeSharedRegon(seed);
    else if (compact.includes("krs")) record[key] = makeSharedKrs(seed);
    else if (compact.includes("dowoduosobistego") || compact.includes("idcard")) record[key] = index % 8 === 0 ? "" : makeIdCard(identitySeed + key.length);
    else if (compact.includes("paszport") || compact.includes("passport")) record[key] = index % 5 === 0 ? "" : makePassport(identitySeed + key.length);
  }
}

function normalizeNames(record, headers, index, seed = index) {
  const personCache = new Map();
  const company = companyInfoFor(seed);
  const getPerson = (key) => {
    const compact = keyId(key);
    const prefix = personIdentityPrefix(compact) || personFieldPrefix(compact);
    if (!personCache.has(prefix)) {
      const identitySeed = personIdentitySeed(seed, compact);
      const female = isFemaleIndex(identitySeed);
      personCache.set(prefix, personFor(identitySeed, female, identitySeed));
    }
    return personCache.get(prefix);
  };

  for (const key of headers) {
    const compact = keyId(key);
    if (compact === "plec") {
      record[key] = isFemaleIndex(personIdentitySeed(seed, compact)) ? "K" : "M";
    }
  }

  for (const key of headers) {
    const compact = keyId(key);
    const person = getPerson(key);
    const relatedPartyNameMatch = String(key).match(/^WspolnikPodmiot(\d+)_Nazwa$/i);
    if (relatedPartyNameMatch) {
      record[key] = companyInfoFor(relatedCompanySeed(seed, Number(relatedPartyNameMatch[1]))).full;
    }
    else if (compact === "imieojca") record[key] = pick(MALE_FIRST_NAMES, personIdentitySeed(seed, compact) + 3);
    else if (compact === "imiematki") record[key] = pick(FEMALE_FIRST_NAMES, personIdentitySeed(seed, compact) + 7);
    else if (compact === "miejsceurodzenia") record[key] = addressParts(personIdentitySeed(seed, compact)).city;
    else if (compact === "obywatelstwo") record[key] = "PL";
    else if (
      compact === "drugieimie"
      || compact === "secondname"
      || compact === "middlename"
      || compact.endsWith("drugieimie")
      || compact.endsWith("secondname")
      || compact.endsWith("middlename")
      || compact.startsWith("drugieimie")
      || compact.startsWith("secondname")
      || compact.startsWith("middlename")
    ) record[key] = duplicatedPersonTextVariant(person.second, index, compact);
    else if (compact === "imie" || compact.endsWith("imie") || compact.startsWith("imie")) record[key] = duplicatedPersonTextVariant(person.first, index, compact);
    else if (compact === "nazwiskorodowe" || compact.endsWith("nazwiskorodowe")) record[key] = duplicatedPersonTextVariant(familyNameFor(personIdentitySeed(seed, compact), isFemaleIndex(personIdentitySeed(seed, compact)), person), index, compact);
    else if (compact === "nazwisko" || compact.endsWith("nazwisko") || compact.startsWith("nazwisko")) record[key] = duplicatedPersonTextVariant(person.last, index, compact);
    else if (compact === "name" || compact === "legalname" || compact === "nazwa" || compact.includes("firmanazwa")) record[key] = company.full;
    else if (compact.includes("nazwaskrocona") || compact.includes("skroconanazwa")) record[key] = company.short;
    else if (compact === "formaprawna" || compact === "entitylegalformcode" || compact === "legalentitytype") record[key] = company.legalForm;
    else if (compact === "status" || compact === "statusvat" || compact === "registrationstatus") record[key] = "AKTYWNY";
    else if (compact === "email" || compact.includes("email")) {
      const emailPerson = personCache.get("firmawlasciciel") || personCache.get("") || personFor(seed, isFemaleIndex(seed));
      const hasPersonalColumns = headers.some((header) => {
        const id = keyId(header);
        return id === "imie" || id.endsWith("imie") || id === "nazwisko" || id.endsWith("nazwisko") || id.includes("wlasciciel");
      });
      record[key] = hasPersonalColumns ? emailForPerson(seed, company.base, emailPerson) : emailForCompany(seed, company.base);
    }
    else if (compact === "stronawww" || compact === "www" || compact.endsWith("www") || compact.includes("website") || compact.includes("url")) record[key] = index % 6 === 0 ? "" : websiteFor(seed, company.base);
  }

}

function cloneRecord(base, headers, index, register) {
  const record = Object.fromEntries(headers.map((h) => [h, base[h] ?? ""]));
  const seed = register === "pesel" ? personSeedFor(index) : companySeedFor(index);
  normalizeNames(record, headers, index, seed);
  setAddress(record, headers, seed);
  normalizeDates(record, headers, index, seed, register);
  enforceDateChronology(record, headers, index);
  normalizeIdentifiers(record, headers, index, seed);
  for (const key of headers) {
    const compact = keyId(key);
    if (
      (/(^|[^A-Za-z])id$/i.test(key) || key === "firma.id")
      && compact !== "registrationauthorityid"
      && compact !== "registrationauthorityentityid"
    ) {
      record[key] = `${key.replace(/[^A-Za-z0-9]/g, "").toUpperCase()}-${pad(index + 1, 5)}`;
    }
    if (key === "Numer agenta") record[key] = `${pad(10000000 + index, 8)}/A/${pad(300000 + index, 6)}`;
  }
  if (register === "krs") {
    enforceKrsRoleCardinality(record, headers);
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

function applyAnomalies(records, headers, register = "") {
  const total = records.length;
  const registerOffset = stableHash(register) % 997;
  const typoIndexes = selectIndexes(total, Math.round(total * 0.02), 7);
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
    if (/^liczba/.test(id)) return false;
    return !/(pesel|nip|regon|krs|lei|dowod|data|date|email|telefon|phone|kod|adres|address|www|url|status|plec|obywatelstwo|imieojca|imiematki)/.test(id);
  });
  for (const i of typoIndexes) {
    const candidates = typoFields.filter((h) => String(records[i][h] ?? "").length > 4);
    if (candidates.length) {
      const key = candidates[Math.floor(rand() * candidates.length)];
      records[i][key] = typo(records[i][key]);
    }
  }

  const nullableFields = headers.filter((h) => !/^Liczba[A-Z]/.test(String(h)));
  for (const i of incompleteRecordIndexes) {
    const candidates = nullableFields.filter((h) => {
      const id = keyId(h);
      return String(records[i][h] ?? "").trim() !== "";
    });
    if (candidates.length) {
      const key = candidates[Math.floor(rand() * candidates.length)];
      records[i][key] = "";
    }
  }

  applyGleifRegisteredAsAnomalies(records, headers);

  const emailFields = headers.filter((h) => keyId(h).includes("email"));
  const emailRefs = [];
  for (let rowIndex = 0; rowIndex < records.length; rowIndex += 1) {
    for (const field of emailFields) {
      if (records[rowIndex][field]) emailRefs.push([rowIndex, field]);
    }
  }
  const badEmailCount = Math.round(emailRefs.length * 0.01);
  const badEmailIndexes = selectIndexes(emailRefs.length, badEmailCount, 131);
  const badEmailIndexSet = new Set(badEmailIndexes);
  for (let i = 0; i < badEmailIndexes.length; i += 1) {
    const [rowIndex, field] = emailRefs[badEmailIndexes[i]];
    records[rowIndex][field] = breakEmail(records[rowIndex][field], i);
  }
  const missingDomainCount = Math.round(emailRefs.length * 0.02);
  const missingDomainIndexes = selectIndexes(emailRefs.length, missingDomainCount, 149)
    .filter((idx) => !badEmailIndexSet.has(idx));
  for (let i = 0; i < missingDomainIndexes.length; i += 1) {
    const [rowIndex, field] = emailRefs[missingDomainIndexes[i]];
    records[rowIndex][field] = replaceEmailDomainWithMissing(records[rowIndex][field], i);
  }

  const idGroups = {
    pesel: headers.filter((h) => keyId(h).includes("pesel")),
    lei: headers.filter((h) => keyId(h).includes("lei")),
    nip: headers.filter((h) => keyId(h).includes("nip")),
    regon: headers.filter((h) => keyId(h).includes("regon")),
    krs: headers.filter((h) => keyId(h).includes("krs")),
    idCard: headers.filter((h) => /(dowoduosobistego|idcard)/.test(keyId(h))),
    passport: headers.filter((h) => /(paszport|passport)/.test(keyId(h))),
  };
  const offsets = { pesel: 59, lei: 67, nip: 71, regon: 89, krs: 97, idCard: 107, passport: 109 };
  for (const [type, fields] of Object.entries(idGroups)) {
    const refs = [];
    for (let rowIndex = 0; rowIndex < records.length; rowIndex += 1) {
      for (const field of fields) {
        if (records[rowIndex][field]) refs.push([rowIndex, field]);
      }
    }
    if (!refs.length) continue;

    const badRate = type === "pesel" || type === "idCard" || type === "passport" || type === "nip" || type === "regon" || type === "krs" || type === "lei"
      ? HARD_PERSON_CONFLICT_RATE
      : 0.02;
    const badCount = Math.round(refs.length * badRate);
    const missingCount = type === "pesel" || type === "lei" ? 0 : Math.round(refs.length * 0.005);
    const badIndexes = new Set(selectIndexes(refs.length, badCount, offsets[type] + registerOffset));
    const missingIndexes = selectIndexes(refs.length, missingCount, offsets[type] + 17)
      .filter((idx) => !badIndexes.has(idx));

    for (const refIndex of badIndexes) {
      const [rowIndex, field] = refs[refIndex];
      records[rowIndex][field] = type === "krs"
        ? breakKrsFormat(records[rowIndex][field])
        : breakDigit(records[rowIndex][field]);
    }
    for (const refIndex of missingIndexes) {
      const [rowIndex, field] = refs[refIndex];
      records[rowIndex][field] = "";
    }
  }

  if (register === "krs") {
    for (const record of records) {
      enforceKrsRoleCardinality(record, headers);
    }
  }
}

function applyGleifRegisteredAsAnomalies(records, headers) {
  const registeredAtField = headers.find((h) => keyId(h) === "registeredat");
  const registeredAsField = headers.find((h) => keyId(h) === "registeredas");
  if (!registeredAtField || !registeredAsField) return;

  const refs = [];
  for (let rowIndex = 0; rowIndex < records.length; rowIndex += 1) {
    if (String(records[rowIndex][registeredAsField] ?? "").trim() !== "") {
      refs.push(rowIndex);
    }
  }
  const badIndexes = selectIndexes(refs.length, Math.max(1, Math.round(refs.length * 0.02)), 211);
  for (const refIndex of badIndexes) {
    const rowIndex = refs[refIndex];
    const registeredAt = String(records[rowIndex][registeredAtField] ?? "").toUpperCase();
    if (registeredAt.includes("RA000466") || registeredAt.includes("KRS") || registeredAt.includes("COURT REGISTER")) {
      records[rowIndex][registeredAsField] = String(records[rowIndex][registeredAsField]).slice(0, -1);
    } else {
      records[rowIndex][registeredAsField] = breakDigit(records[rowIndex][registeredAsField]);
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

const identityPool = new Map();

function getOrCreateSharedIdentity(pesel, sourceRecord, headers) {
  if (!pesel) return null;
  
  if (identityPool.has(pesel)) {
    return identityPool.get(pesel);
  }

  const identity = {
    imie: sourceRecord[headers.find(h => FIELD_PATTERNS.imie.test(h) || FIELD_PATTERNS.imie.test(keyId(h)))] ?? "",
    drugieImie: sourceRecord[headers.find(h => FIELD_PATTERNS.drugieImie.test(h) || FIELD_PATTERNS.drugieImie.test(keyId(h)))] ?? "",
    nazwisko: sourceRecord[headers.find(h => FIELD_PATTERNS.nazwisko.test(h) || FIELD_PATTERNS.nazwisko.test(keyId(h)))] ?? "",
    dataUrodzenia: sourceRecord[headers.find(h => FIELD_PATTERNS.dataUrodzenia.test(h) || FIELD_PATTERNS.dataUrodzenia.test(keyId(h)))] ?? "",
    plec: sourceRecord[headers.find(h => FIELD_PATTERNS.plec.test(h) || FIELD_PATTERNS.plec.test(keyId(h)))] ?? "",
  };

  const establishmentHeader = headers.find(h => /Establishment_Date/i.test(h) || /data.*zaloz/i.test(h));
  const deregistrationHeader = headers.find(h => /Deregistration_Date/i.test(h) || /data.*wyrej/i.test(h));

  if (establishmentHeader && deregistrationHeader) {
    const startDateRaw = sourceRecord[establishmentHeader];
    const endDateRaw = sourceRecord[deregistrationHeader];

    if (startDateRaw && endDateRaw) {
      const startSec = Date.parse(startDateRaw);
      const endSec = Date.parse(endDateRaw);

      if (!isNaN(startSec) && !isNaN(endSec) && startSec > endSec) {
        sourceRecord[establishmentHeader] = endDateRaw;
        sourceRecord[deregistrationHeader] = startDateRaw;
      }
    }
  }

  const pierwImie = identity.imie.trim();
  const sugerujeKobiete = identity.plec.toLowerCase().startsWith('k') || 
                          identity.plec.toLowerCase().startsWith('f') || 
                          (pierwImie.endsWith('a') && pierwImie.toLowerCase() !== 'jan');

  if (identity.drugieImie) {
    identity.drugieImie = secondNameForGender(identity.drugieImie, stableHash(pesel), sugerujeKobiete);
  }

  if (sugerujeKobiete) {
    identity.nazwisko = identity.nazwisko.replace(/ski$/, 'ska').replace(/cki$/, 'cka').replace(/dzki$/, 'dzka');
    if (!identity.plec) identity.plec = "K";
  } else {
    identity.nazwisko = identity.nazwisko.replace(/ska$/, 'ski').replace(/cka$/, 'cki').replace(/dzka$/, 'dzki');
    if (!identity.plec) identity.plec = "M";
  }

  identityPool.set(pesel, identity);
  return identity;
}


function injectIdentity(record, headers, identity) {
  if (!identity) return;

  for (const field of headers) {
    const id = keyId(field);
    if (FIELD_PATTERNS.imie.test(field) || FIELD_PATTERNS.imie.test(id)) record[field] = identity.imie;
    if (FIELD_PATTERNS.drugieImie.test(field) || FIELD_PATTERNS.drugieImie.test(id)) record[field] = identity.drugieImie ?? "";
    if (FIELD_PATTERNS.nazwisko.test(field) || FIELD_PATTERNS.nazwisko.test(id)) record[field] = identity.nazwisko;
    if (FIELD_PATTERNS.dataUrodzenia.test(field) || FIELD_PATTERNS.dataUrodzenia.test(id)) record[field] = identity.dataUrodzenia;
    if (FIELD_PATTERNS.plec.test(field) || FIELD_PATTERNS.plec.test(id)) record[field] = identity.plec;
  }
}

const FIELD_PATTERNS = {
  pesel: /(pesel)/i,
  nip: /(nip)/i,
  regon: /(regon)/i,
  imie: /^(?!.*(drugie|sec|2)).*(imie|first.*name)/i, 
  drugieImie: /(drugie.*imie|second.*name|middle.*name|imie.*2)/i,
  nazwisko: /(nazwisko|last.*name)/i,
  dataUrodzenia: /(dataurodzenia|birth.*date)/i,
  plec: /(plec|gender)/i,
  nazwaFirmy: /(nazwa.*firmy|nazwa.*pelna|nazwa.*skrocona|company.*name|legal.*name|nazwa)/i
};

function main() {
  console.log("Rozpoczynam działanie skryptu...");

  const registers = fs.readdirSync(path.join(DATA_DIR, "csv"))
    .filter((name) => name.endsWith(".csv"))
    .map((name) => path.basename(name, ".csv").toUpperCase())
    .sort();
    
  const manifest = Object.fromEntries(FORMATS.map((format) => [format, {}]));
  const preparedRecords = {};
  const headersMap = {};

  for (const register of registers) {
    const registerLower = register.toLowerCase();
    const { headers, records: sourceRecords } = readRecords(registerLower);
    headersMap[register] = headers;
    preparedRecords[register] = [];

    console.log(`Wczytano rejestr [${register}]: ${sourceRecords.length} rekordów źródłowych.`);

    for (let i = 0; i < TARGET_PER_REGISTER; i += 1) {
      const rawClone = cloneRecord(sourceRecords[i % sourceRecords.length], headers, i, registerLower);
      const cloned = JSON.parse(JSON.stringify(rawClone));
      preparedRecords[register].push(cloned);
    }
  }

  const personsPool = new Map();
  const companiesPool = new Map();

  for (const register of registers) {
    const records = preparedRecords[register];
    const headers = headersMap[register];
    
    const hPesel = headers.find(h => FIELD_PATTERNS.pesel.test(h) || FIELD_PATTERNS.pesel.test(keyId(h)));
    const hNip = headers.find(h => FIELD_PATTERNS.nip.test(h) || FIELD_PATTERNS.nip.test(keyId(h)));
    const hRegon = headers.find(h => FIELD_PATTERNS.regon.test(h) || FIELD_PATTERNS.regon.test(keyId(h)));
    const hImie = headers.find(h => FIELD_PATTERNS.imie.test(h) || FIELD_PATTERNS.imie.test(keyId(h)));
    const hDrugieImie = headers.find(h => FIELD_PATTERNS.drugieImie.test(h) || FIELD_PATTERNS.drugieImie.test(keyId(h)));
    const hNazwisko = headers.find(h => FIELD_PATTERNS.nazwisko.test(h) || FIELD_PATTERNS.nazwisko.test(keyId(h)));
    const hPlec = headers.find(h => FIELD_PATTERNS.plec.test(h) || FIELD_PATTERNS.plec.test(keyId(h)));
    const hNazwa = headers.find(h => FIELD_PATTERNS.nazwaFirmy.test(h) || FIELD_PATTERNS.nazwaFirmy.test(keyId(h)));

    for (const rec of records) {
      if (hPesel && rec[hPesel] && hImie && hNazwisko && rec[hImie] && rec[hNazwisko]) {
        const pKey = String(rec[hPesel]).trim();
        if (!personsPool.has(pKey)) {
          const firstGender = firstNameGender(rec[hImie]);
          const female = hPlec && rec[hPlec]
            ? String(rec[hPlec]).trim().toLowerCase().startsWith("k")
            : firstGender === "female";
          personsPool.set(pKey, { 
            imie: String(rec[hImie]).trim(), 
            drugieImie: hDrugieImie && rec[hDrugieImie] ? secondNameForGender(rec[hDrugieImie], stableHash(pKey), female) : "",
            nazwisko: String(rec[hNazwisko]).trim() 
          });
        }
      }
      
      const compKey = (hNip && rec[hNip]) ? String(rec[hNip]).trim() : ((hRegon && rec[hRegon]) ? String(rec[hRegon]).trim() : null);
      if (compKey && hNazwa && rec[hNazwa] && String(rec[hNazwa]).trim() !== "") {
        if (!companiesPool.has(compKey)) {
          companiesPool.set(compKey, { 
            nazwa: String(rec[hNazwa]).trim() 
          });
        }
      }
    }
  }

  console.log(`Zbudowano pulę referencyjną: ${personsPool.size} osób, ${companiesPool.size} firm.`);

  const allPesels = Array.from(personsPool.keys());
  const allCompanyKeys = Array.from(companiesPool.keys());

  for (const register of registers) {
    const records = preparedRecords[register];
    const headers = headersMap[register];
    
    const hPesel = headers.find(h => FIELD_PATTERNS.pesel.test(h) || FIELD_PATTERNS.pesel.test(keyId(h)));
    const hNip = headers.find(h => FIELD_PATTERNS.nip.test(h) || FIELD_PATTERNS.nip.test(keyId(h)));
    const hRegon = headers.find(h => FIELD_PATTERNS.regon.test(h) || FIELD_PATTERNS.regon.test(keyId(h)));
    const hImie = headers.find(h => FIELD_PATTERNS.imie.test(h) || FIELD_PATTERNS.imie.test(keyId(h)));
    const hDrugieImie = headers.find(h => FIELD_PATTERNS.drugieImie.test(h) || FIELD_PATTERNS.drugieImie.test(keyId(h)));
    const hNazwisko = headers.find(h => FIELD_PATTERNS.nazwisko.test(h) || FIELD_PATTERNS.nazwisko.test(keyId(h)));
    const hNazwa = headers.find(h => FIELD_PATTERNS.nazwaFirmy.test(h) || FIELD_PATTERNS.nazwaFirmy.test(keyId(h)));

    const isBusinessSystem = ["KRS", "CEIDG", "REGON", "VAT", "GLEIF", "INSURANCE_CORE"].includes(register);
    const linkRate = isBusinessSystem ? 0.30 : 0.05; 
    const targetLinkCount = Math.round(records.length * linkRate);

    for (let i = 0; i < records.length; i++) {
      const rec = records[i];

      if (i < targetLinkCount) {
        if (hPesel && allPesels.length > 0) {
          const sharedPesel = allPesels[i % allPesels.length];
          const identity = personsPool.get(sharedPesel);
          
          if (identity) {
            rec[hPesel] = sharedPesel;
            if (hImie) rec[hImie] = identity.imie;
            if (hDrugieImie) rec[hDrugieImie] = identity.drugieImie;
            if (hNazwisko) rec[hNazwisko] = identity.nazwisko;
          }
        }
        
        if ((hNip || hRegon) && allCompanyKeys.length > 0) {
          const sharedCompKey = allCompanyKeys[i % allCompanyKeys.length];
          const compIdentity = companiesPool.get(sharedCompKey);
          
          if (compIdentity) {
            if (sharedCompKey.length === 10) {
              if (hNip) rec[hNip] = sharedCompKey;
              if (hRegon) rec[hRegon] = ""; 
            } else if (sharedCompKey.length === 9 || sharedCompKey.length === 14) {
              if (hRegon) rec[hRegon] = sharedCompKey;
              if (hNip) rec[hNip] = ""; 
            }
            if (hNazwa) rec[hNazwa] = compIdentity.nazwa;
          }
        }
      } 
      else {
        if (hPesel && rec[hPesel] && personsPool.has(String(rec[hPesel]).trim())) {
          const identity = personsPool.get(String(rec[hPesel]).trim());
          if (identity) {
            if (hImie) rec[hImie] = identity.imie;
            if (hDrugieImie) rec[hDrugieImie] = identity.drugieImie;
            if (hNazwisko) rec[hNazwisko] = identity.nazwisko;
          }
        }
        
        const currentCompKey = (hNip && rec[hNip]) ? String(rec[hNip]).trim() : ((hRegon && rec[hRegon]) ? String(rec[hRegon]).trim() : null);
        if (currentCompKey && companiesPool.has(currentCompKey)) {
          const compIdentity = companiesPool.get(currentCompKey);
          if (compIdentity && hNazwa) rec[hNazwa] = compIdentity.nazwa;
        }
      }
    }
  }

  for (const register of registers) {
    const records = preparedRecords[register];
    const headers = headersMap[register];
    const registerLower = register.toLowerCase();

    applyAnomalies(records, headers, registerLower);

    const counts = writeRegister(registerLower, headers, records);
    for (const format of FORMATS) manifest[format][registerLower] = counts[format];
    console.log(`Zapisano system: [${register}] - ${records.length} rekordów.`);
  }

  fs.rmSync(path.join(DATA_DIR, ".xlsx-tmp"), { recursive: true, force: true });
  fs.writeFileSync(path.join(DATA_DIR, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  console.log("Skrypt zakończył działanie z sukcesem!");
}

try {
  main();
} catch (error) {
  console.error("KRYTYCZNY BŁĄD PODCZAS WYKONYWANIA SKRYPTU:", error);
}
