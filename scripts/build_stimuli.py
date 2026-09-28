"""First-pass Turkish stimulus table for the Harpaintner 293-word set.

HISTORICAL RECORD. data/stimuli_tr.csv is the source of truth: edit that file,
not this one. This script refuses to overwrite it without --force.

Columns
  english       stimulus as it appears in human_norms.csv
  turkish       the form fed to the model
  alternative   a second defensible translation, if any
  origin        native | hybrid | loan-arabic | loan-persian | loan-french | loan-other
                native  = Turkic root (often with a Turkish derivational suffix)
                hybrid  = borrowed root + Turkish suffix (e.g. rahat + -lık)
  concrete_root the concrete or perceptual root visible inside a native word, if any
                (e.g. izlenim <- iz "footprint"). Empty = no transparent concrete root.
  flag          ok    = confident one-to-one
                check = defensible but a native speaker should confirm
                hard  = no clean one-to-one; English is polysemous or Turkish splits the sense
  note          why it is flagged

Origins are a first pass and must be checked against Nisanyan Sozlugu before
they are used for the native-versus-borrowed contrast.
"""
import csv, os, sys

ROWS = r"""
ability|kabiliyet|yeti|loan-arabic||check|'yetenek' reserved for talent to avoid a duplicate target
accusation|suçlama||native|suç (crime)|ok|
achievement|kazanım|başarı|native|kazan- (earn)|check|'başarı' reserved for success; the two collapse in Turkish
activity|etkinlik|faaliyet|native||check|reform-era coinage; 'faaliyet' is the older loan
addiction|bağımlılık||native|bağ (tie, rope)|ok|
admiration|hayranlık||hybrid||ok|
advantage|avantaj|üstünlük|loan-french||check|
adventure|macera||loan-arabic||ok|
advice|öğüt|nasihat|native||check|'tavsiye' reserved for recommendation
agony|ıstırap||loan-arabic||ok|
agreement|anlaşma|mutabakat|native|anla- (understand)|ok|
amazement|hayret||loan-arabic||check|cluster with astonishment, surprise, wonder
ambition|hırs|tutku|loan-arabic||check|'hırs' leans more negative than English 'ambition'
ambush|pusu||native||ok|
amusement|eğlence||native|eğlen- (be diverted)|check|shares a field with fun
anger|öfke||native||ok|
anxiety|kaygı|endişe|native||ok|
apology|özür||loan-arabic||ok|
appearance|görünüm|görünüş|native|gör- (see)|ok|
appetite|iştah||loan-persian||ok|Arabic via Persian
application|başvuru|uygulama|native|baş (head) + vur- (strike)|hard|English splits job application / applying a method
aptitude|yatkınlık||native|yat- (lie down, incline)|check|
argument|tartışma|argüman|native|tart- (weigh)|hard|quarrel vs logical argument
art|sanat||loan-arabic||ok|
aspect|yön|boyut|native||hard|no clean single-word equivalent
assassination|suikast||loan-arabic||ok|
assumption|varsayım||native|var (existing) + say- (count)|ok|reform-era coinage
astonishment|şaşkınlık||native|şaş- (be confused)|check|cluster with amazement, surprise, wonder
attack|saldırı||native|saldır- (charge)|ok|
attention|dikkat||loan-arabic||ok|
attraction|çekim|cazibe|native|çek- (pull)|check|'çekim' is also physical/gravitational pull
beauty|güzellik||native|güzel (beautiful)|ok|
being|varlık||native|var (existing)|check|philosophical sense
betrayal|ihanet||loan-arabic||ok|
blackmail|şantaj||loan-french||ok|
boredom|can sıkıntısı|bıkkınlık|hybrid|sık- (squeeze)|check|two-word form; 'can' is Persian, 'sık-' native
boycott|boykot||loan-other||ok|
bravery|yiğitlik|kahramanlık|native|yiğit (young brave man)|check|'cesaret' reserved for courage
career|kariyer||loan-french||ok|
carefulness|özen|dikkatlilik|native||check|
catastrophe|felaket|afet|loan-arabic||ok|
caution|temkin|ihtiyat|loan-arabic||check|
challenge|meydan okuma|zorluk|hybrid|oku- (call out)|hard|no single noun; 'zorluk' reserved for difficulty
chaos|kaos||loan-other||ok|Greek via French
character|karakter||loan-french||ok|
charm|çekicilik|cazibe|native|çek- (pull)|check|
comfort|rahatlık|konfor|hybrid||ok|
commitment|bağlılık|taahhüt|native|bağ (tie, rope)|check|legal sense would be 'taahhüt'
comparison|karşılaştırma||native|karşı (opposite)|ok|
compassion|şefkat|acıma|loan-arabic||check|'merhamet' reserved for mercy
competence|yetkinlik||native|yet- (reach, suffice)|ok|reform-era coinage
compromise|uzlaşma|taviz|native||ok|
compulsion|zorlantı|zorlama|hybrid||hard|clinical OCD sense vs coercion
confession|itiraf||loan-arabic||ok|
conflict|çatışma||native|çat- (knock together)|ok|
consideration|düşüncelilik|değerlendirme|native|düşün- (think)|hard|considerateness vs deliberation; check the German original
consolation|teselli||loan-arabic||ok|
contempt|küçümseme|aşağılama|native|küçük (small)|ok|
convention|teamül|uzlaşım|loan-arabic||hard|social convention vs meeting; 'teamül' is formal
cooperation|işbirliği||native|iş (work) + bir (one)|ok|
courage|cesaret||loan-arabic||ok|
creativity|yaratıcılık||native|yarat- (create)|ok|
crime|suç||native||ok|
criticism|eleştiri||native|ele- (sieve)|ok|reform-era coinage
cruelty|zulüm|acımasızlık|loan-arabic||ok|
culture|kültür||loan-french||ok|
curiosity|merak||loan-arabic||ok|
custom|âdet|görenek|loan-arabic||check|'gelenek' reserved for tradition
danger|tehlike||loan-arabic||ok|
death|ölüm||native|öl- (die)|ok|
decision|karar||loan-arabic||ok|
demand|talep|istem|loan-arabic||check|request vs economic demand
desire|arzu|istek|loan-persian||ok|
desperation|çaresizlik||hybrid||ok|
destruction|yıkım||native|yık- (knock down)|ok|
detection|tespit|saptama|loan-arabic||check|
dictatorship|diktatörlük||hybrid||ok|
difference|fark|ayrım|loan-arabic||ok|
difficulty|zorluk||hybrid||ok|'zor' is Persian
dignity|haysiyet|saygınlık|loan-arabic||check|'onur' reserved for honor
diligence|çalışkanlık||native|çalış- (work)|ok|
disadvantage|dezavantaj||loan-french||ok|
disappointment|hayal kırıklığı||hybrid|kır- (break)|ok|'hayal' Arabic, 'kır-' native
discovery|keşif||loan-arabic||ok|
disgust|iğrenme|tiksinti|native|iğren- (be repelled)|ok|
dismay|yılgınlık||native|yıl- (be daunted)|hard|no close single-word equivalent
dispute|anlaşmazlık|ihtilaf|native|anla- (understand)|ok|
distance|mesafe|uzaklık|loan-arabic||ok|
distraction|dikkat dağınıklığı||hybrid|dağıl- (scatter)|check|two-word form
diversity|çeşitlilik||hybrid||ok|
doubt|şüphe|kuşku|loan-arabic||ok|
downfall|çöküş||native|çök- (collapse)|ok|
dream|rüya|hayal|loan-arabic||hard|night dream vs aspiration; German 'Traum' has the same split
duty|vazife|ödev|loan-arabic||check|'görev' reserved for task
eagerness|heves||loan-arabic||check|
effort|çaba||native||ok|
elegance|zarafet||loan-arabic||ok|
emotion|duygu||native|duy- (hear, feel)|ok|
enchantment|büyülenme||native|büyü (spell)|check|
enthusiasm|coşku||native|coş- (boil over)|ok|
envy|haset|gıpta|loan-arabic||check|'kıskançlık' reserved for jealousy
error|hata||loan-arabic||ok|
event|olay||native|ol- (happen)|ok|reform-era coinage
excitement|heyecan||loan-arabic||ok|
expectation|beklenti||native|bekle- (wait)|ok|
experience|deneyim|tecrübe|native|dene- (try)|ok|reform-era coinage
explanation|açıklama||native|açık (open)|ok|
exploitation|sömürü||native|sömür- (gnaw)|ok|
faithfulness|sadakat||loan-arabic||ok|
fantasy|fantezi|hayal gücü|loan-french||check|
fate|kader||loan-arabic||ok|
fear|korku||native|kork- (fear)|ok|
fight|kavga|dövüş|loan-persian||ok|
fitness|zindelik|form|hybrid||check|
flexibility|esneklik||native|esne- (stretch)|ok|
force|kuvvet||loan-arabic||check|'güç' reserved for power
forgiveness|bağışlama|affetme|native|bağışla- (grant)|ok|
freedom|özgürlük|hürriyet|native|öz (self)|ok|
fright|ürküntü||native|ürk- (startle)|check|cluster with fear, horror, panic
frustration|hüsran|engellenmişlik|loan-arabic||hard|no close single-word equivalent
fun|keyif|eğlence|loan-arabic||hard|'eğlence' reserved for amusement
fury|hiddet||loan-arabic||check|cluster with anger, rage
future|gelecek|istikbal|native|gel- (come)|ok|
genius|deha||loan-arabic||check|quality, not the person ('dâhi')
glory|şan|şeref|loan-arabic||check|
grace|incelik|lütuf|native|ince (thin, fine)|hard|elegance vs divine grace; 'zarafet' reserved for elegance
gratitude|minnettarlık|şükran|hybrid||ok|
greed|açgözlülük||native|aç (hungry) + göz (eye)|ok|
guess|tahmin||loan-arabic||ok|
habit|alışkanlık||native|alış- (get used to)|ok|
happiness|mutluluk||native||check|origin of 'mutlu' should be confirmed
hate|nefret||loan-arabic||ok|
help|yardım||native||check|origin should be confirmed
hint|ipucu||native|ip (thread) + uç (end)|ok|
home|yuva|ev|native||hard|home vs house; 'yuva' is also nest
honor|onur|şeref|loan-french||ok|from French honneur
hope|umut|ümit|native||ok|
horror|dehşet||loan-arabic||ok|
humor|mizah||loan-arabic||ok|
hunger|açlık||native|aç (hungry)|ok|
hurry|acele|telaş|loan-arabic||ok|
idea|fikir||loan-arabic||ok|
ideal|ülkü|ideal|native||check|'ülkü' is dated and politically coloured; 'ideal' is the everyday word
illusion|yanılsama|illüzyon|native|yanıl- (err)|ok|reform-era coinage
impression|izlenim||native|iz (footprint, trace)|ok|reform-era coinage
incentive|teşvik|özendirme|loan-arabic||ok|
independence|bağımsızlık||native|bağ (tie, rope)|ok|
indifference|kayıtsızlık|ilgisizlik|hybrid||ok|
influence|etki||native|et- (do)|ok|reform-era coinage
insanity|delilik||native|deli (mad)|ok|
insight|içgörü||native|iç (inside) + gör- (see)|ok|reform-era calque
insult|hakaret||loan-arabic||ok|
insurrection|ayaklanma||native|ayak (foot)|ok|
intention|niyet||loan-arabic||ok|
interest|ilgi||native||check|not financial interest ('faiz')
invention|buluş|icat|native|bul- (find)|ok|
jealousy|kıskançlık||native|kıskan- (begrudge)|ok|
joy|sevinç||native|sevin- (rejoice)|ok|
judgement|yargı||native|yar- (split)|ok|
justice|adalet||loan-arabic||ok|
justification|gerekçe||native|gerek (need)|ok|
kindness|iyilik|nezaket|native|iyi (good)|check|'iyilik' leans toward goodness or a good deed
knowledge|bilgi||native|bil- (know)|ok|
love|sevgi|aşk|native|sev- (love)|check|'aşk' is romantic love
luck|şans|talih|loan-french||ok|
lust|şehvet||loan-arabic||ok|
luxury|lüks||loan-french||ok|
magic|büyü||native||ok|
manipulation|manipülasyon|yönlendirme|loan-french||ok|
manners|görgü|terbiye|native|gör- (see)|ok|
matter|mesele|madde|loan-arabic||hard|issue vs physical matter
meanness|alçaklık|cimrilik|native|alçak (low)|check|baseness vs stinginess
memory|anı|hafıza|native|an- (recall)|hard|a memory vs the faculty
menace|gözdağı||native|göz (eye) + dağ (brand)|check|'tehdit' reserved for threat
mercy|merhamet||loan-arabic||ok|
miracle|mucize||loan-arabic||ok|
misdemeanor|kabahat||loan-arabic||ok|
misery|sefalet||loan-arabic||check|'sefalet' leans toward squalor
mockery|alay||loan-arabic||check|origin should be confirmed
model|model|örnek|loan-french||hard|role model vs fashion model vs scientific model
moment|an||native||ok|
mood|ruh hali|keyif|loan-arabic||check|two-word form
mourning|yas||loan-persian||ok|
need|ihtiyaç|gereksinim|loan-arabic||ok|
nervousness|gerginlik|sinirlilik|native|ger- (stretch taut)|ok|
nightmare|kâbus||loan-arabic||ok|
notion|kavram||native|kavra- (grasp)|ok|reform-era coinage
obedience|itaat||loan-arabic||ok|
objection|itiraz||loan-arabic||ok|
obligation|yükümlülük|zorunluluk|native|yük (load)|ok|
observation|gözlem||native|göz (eye)|ok|reform-era coinage
occupation|meslek|işgal|loan-arabic||hard|job vs military occupation
order|düzen|emir|native|düz (flat, straight)|hard|orderliness vs command vs sequence
ostracism|dışlanma||native|dış (outside)|ok|
overview|genel bakış||native|bak- (look)|ok|two-word form
pain|acı||native||ok|
panic|panik||loan-french||ok|
pardon|af||loan-arabic||ok|
passion|tutku||native|tut- (hold)|ok|
past|geçmiş||native|geç- (pass)|ok|
peace|barış||native||ok|
perception|algı||native|al- (take)|ok|reform-era coinage
perfection|mükemmellik|kusursuzluk|hybrid||ok|
performance|performans|başarım|loan-french||check|
perspective|bakış açısı||native|bak- (look) + açı (angle)|ok|two-word form
plan|plan||loan-french||ok|
pleasure|zevk||loan-arabic||ok|
potential|potansiyel|gizil güç|loan-french||ok|
poverty|yoksulluk||native|yok (absent)|ok|
power|güç||native||ok|
prediction|öngörü|tahmin|native|ön (front) + gör- (see)|ok|reform-era calque; 'tahmin' reserved for guess
present|şimdiki zaman|şimdi|native||hard|time sense only; English also means gift
pride|gurur||loan-arabic||ok|
problem|sorun|problem|native|sor- (ask)|ok|reform-era coinage
prohibition|yasak||native||ok|
promise|vaat|söz|loan-arabic||check|'söz' is more natural but also means 'word'
proof|kanıt||native||ok|reform-era coinage
proposal|öneri||native|ön (front)|ok|reform-era coinage
prosperity|refah||loan-arabic||ok|
protection|koruma||native|koru- (guard)|ok|
protest|protesto||loan-other||ok|Italian
provocation|provokasyon|kışkırtma|loan-french||check|
punishment|ceza||loan-arabic||ok|
quality|nitelik|kalite|native||ok|reform-era coinage
quantity|nicelik|miktar|native||ok|reform-era coinage
rage|hışım||loan-persian||check|cluster with anger, fury
realization|farkındalık|gerçekleştirme|hybrid||hard|becoming aware vs making real
reassurance|güvence||native|güven (trust)|ok|
recommendation|tavsiye|öneri|loan-arabic||ok|
recovery|iyileşme||native|iyi (good)|ok|
regard|itibar|saygı|loan-arabic||hard|'saygı' reserved for respect
regret|pişmanlık||hybrid||ok|
relief|rahatlama||hybrid||ok|
remorse|vicdan azabı||loan-arabic||check|two-word form
requirement|gereklilik|gereksinim|native|gerek (need)|ok|
resemblance|benzerlik||native|benze- (resemble)|ok|
resistance|direniş|direnç|native|diren- (resist)|ok|
resolution|çözüm|karar|native|çöz- (untie)|hard|solution vs firm decision
respect|saygı||native|say- (count, esteem)|ok|
responsibility|sorumluluk||native|sor- (ask)|ok|
retaliation|misilleme||hybrid||ok|
revenge|intikam||loan-arabic||ok|
revolution|devrim|ihtilal|hybrid||check|reform-era coinage on an Arabic root
risk|risk||loan-french||ok|
ritual|ritüel|ayin|loan-french||ok|
romantic|romantiklik|romantizm|hybrid||hard|English stimulus is an adjective
safety|güvenlik||native|güven (trust)|ok|
satisfaction|tatmin|memnuniyet|loan-arabic||ok|
scheme|entrika|düzen|loan-french||hard|plot vs plan
selection|seçim||native|seç- (choose)|check|also means election
self-dependence|kendine yeterlilik|özgüven|native|yet- (suffice)|hard|no settled equivalent; two-word form
sensation|duyum|his|native|duy- (hear, feel)|hard|bodily sensation vs sensational event
sensitivity|duyarlılık||native|duy- (hear, feel)|ok|
shame|utanç||native|utan- (be ashamed)|ok|
shyness|çekingenlik|utangaçlık|native|çekin- (draw back)|ok|
skill|beceri||native|becer- (manage)|ok|
slapstick|kaba güldürü|şamata|native|gül- (laugh)|hard|no settled equivalent; two-word form
solitude|yalnızlık||native|yalnız (alone)|ok|
stability|istikrar|kararlılık|loan-arabic||ok|
stimulus|uyaran|uyarıcı|native|uyar- (rouse)|check|shares a root with warning
stress|stres||loan-french||ok|
success|başarı||native|baş (head)|ok|
suffering|çile|acı çekme|loan-persian||check|'ıstırap' reserved for agony
support|destek||native||check|origin should be confirmed
surprise|sürpriz|şaşırma|loan-french||check|cluster with amazement, astonishment, wonder
talent|yetenek||native|yet- (reach, suffice)|ok|
task|görev||native||ok|
terrorism|terörizm||loan-french||ok|
theory|kuram|teori|native|kur- (build)|ok|reform-era coinage
thirst|susuzluk||native|su (water)|ok|
thought|düşünce||native|düşün- (think)|ok|
threat|tehdit||loan-arabic||ok|
tradition|gelenek||native|gel- (come)|ok|
trend|eğilim|trend|native|eğil- (bend)|ok|
trust|güven||native||ok|
value|değer||native|değ- (touch)|ok|
vanity|kendini beğenmişlik|kibir|native|beğen- (like)|check|two-word form
victory|zafer||loan-arabic||ok|
view|görüş|manzara|native|gör- (see)|check|opinion vs scenery
violation|ihlal||loan-arabic||ok|
violence|şiddet||loan-arabic||ok|
war|savaş||native||ok|
warning|uyarı||native|uyar- (rouse)|ok|
weakness|zayıflık|güçsüzlük|hybrid||ok|
wealth|zenginlik|servet|hybrid||ok|
welfare|esenlik|refah|native|esen (well)|hard|'refah' reserved for prosperity
will|irade||loan-arabic||ok|
willingness|isteklilik||native|iste- (want)|ok|
wish|dilek||native|dile- (wish)|ok|
wit|nükte|espri|loan-arabic||check|
wonder|huşu|hayret|loan-arabic||hard|awe sense; 'hayret' reserved for amazement
work|iş|emek|native||check|
worry|endişe||loan-persian||ok|
"""

def main(out_path, norms_path):
    rows = []
    for line in ROWS.strip().splitlines():
        parts = line.split("|")
        assert len(parts) == 7, f"bad row: {line}"
        rows.append(dict(zip(
            ["english", "turkish", "alternative", "origin", "concrete_root", "flag", "note"], parts)))

    import pandas as pd
    norms = pd.read_csv(norms_path)["word"].astype(str).str.strip().tolist()
    eng = [r["english"] for r in rows]
    missing = sorted(set(norms) - set(eng))
    extra = sorted(set(eng) - set(norms))
    dup_en = sorted({w for w in eng if eng.count(w) > 1})
    tr = [r["turkish"] for r in rows]
    dup_tr = sorted({w for w in tr if tr.count(w) > 1})
    bad_origin = [r for r in rows if r["origin"] not in
                  {"native", "hybrid", "loan-arabic", "loan-persian", "loan-french", "loan-other"}]
    bad_flag = [r for r in rows if r["flag"] not in {"ok", "check", "hard"}]
    print(f"rows={len(rows)} norms={len(norms)} missing={missing} extra={extra}")
    print(f"duplicate english={dup_en} duplicate turkish={dup_tr}")
    print(f"bad origin={len(bad_origin)} bad flag={len(bad_flag)}")
    ok = not (missing or extra or dup_en or dup_tr or bad_origin or bad_flag) and len(rows) == len(norms)
    if not ok:
        sys.exit("VALIDATION FAILED")

    # keep the norms order
    order = {w: i for i, w in enumerate(norms)}
    rows.sort(key=lambda r: order[r["english"]])
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    from collections import Counter
    print("\nflags  :", dict(Counter(r["flag"] for r in rows)))
    print("origins:", dict(Counter(r["origin"] for r in rows)))
    nat_t = sum(1 for r in rows if r["origin"] == "native" and r["concrete_root"])
    print(f"native with a transparent concrete root: {nat_t}")
    print(f"multi-word Turkish forms: {sum(1 for r in rows if ' ' in r['turkish'])}")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    here = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    up = os.environ.get("GG_UPSTREAM", os.path.join(here, "upstream", "grounding-gap"))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "data", "stimuli_tr.csv")
    if os.path.exists(out) and "--force" not in sys.argv:
        sys.exit(f"{out} exists and is the source of truth once edited by hand.\n"
                 "This script only records the first-pass translation. Use scripts/validate_stimuli.py "
                 "to check the current file, or pass --force to overwrite it deliberately.")
    norms = sys.argv[2] if len(sys.argv) > 2 else os.path.join(up, "property_generation_experiments", "data", "experiment_1", "human_norms.csv")
    main(out, norms)
