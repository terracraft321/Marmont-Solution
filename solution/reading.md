# Marmont letter: proposed reading

A proposed reading of the 24 cipher rows in the letter to Marmont, attributed on historical grounds to Eugène’s office in March 1809. The visible opening refers to letters of the 8th, 14th and 20th and addresses General Marmont. The clear closing begins “Sur ce je prie Dieu”. Those passages are not counted as recovered ciphertext. The French below is an editorial reading; TARGET remains unresolved in the literal decoding and its honorific is a contextual proposal.

## French editorial reading

Renfermant les ordres et instructions que [Sa Majesté] m'a chargé de vous donner.

Je m'empresse aujourd'hui de vous donner connaissance de la position d'armées françaises et alliées.

Le duc de Danzig à la tête de quarante mille Bavarois occupe Munich et Passau.

Le prince Poniatowski à la tête de trente mille Polonais est campé sur la Vistule, menaçant Cracovie.

Le prince de Ponte-Corvo commande l'armée saxonne campée en avant de Dresde et le duc d'Auerstaedt occupe Bayreuth avec quatre-vingt mille Français et le duc de Rivoli commande soixante mille hommes cantonnés à Ulm et Donaverth.

Le [général] Oudinot avec le corps d'élite formant quarante mille hommes est à Augsbourg et sur le Lech.

Les Russes marchent sur l'Autriche et l'armée [du] Frioul est aujourd'hui de quatre-vingt mille hommes. Ajoutez à cela le corps d'armée de Dalmatie, sans comprendre les réserves qui s'organisent de toutes parts sur les derrières et vous voyez que l'Autriche sera attaquée à la fois sur tous les points et elle court par conséquent à grands pas vers sa perte et vous ne devez, alors que vous recevrez ordre de marcher, vous en laisser imposer par quelques troupes ou un rassemblement de canailles.

J'attends toujours de vos nouvelles avec impatience.

Les Autrichiens sont toujours à Laybach, Klagenfurth, Villach et Salzburg et semblent menacer le Tyrol par Lintz et cependant on croirait qu'ils songent à porter des troupes en Galicie pour s'opposer aux Russes.

Ces dispositions feraient présager que leur plan de campagne est dérangé avant que la guerre soit encore déclarée et il n'y a toutefois rien encore de positif.

Les milices sont mises en activité et quoiqu'on ait cherché à monter les têtes, il n'est pas encore prouvé que ces levées soyent d'un grand renfort pour l'armée.

## English translation

The English translates the editorial French. Brackets mark selected contextual proposals; all 29 normalized character interventions are listed in reading_alignment.tsv and inputs/editorial_interventions.tsv. Lintz is retained without deciding Linz versus Lienz. Troop strengths and movements are statements in the proposed correspondence, not independently established military facts. The original manuscript, exact date, complete historical codebook, and unique values for every uncertain sign have not been authenticated.

[Those letters] contained the orders and instructions which [His Majesty] charged me to give you. I hasten today to acquaint you with the disposition of French and allied armies. The Duke of Danzig, at the head of forty thousand Bavarians, occupies Munich and Passau. Prince Poniatowski, at the head of thirty thousand Poles, is camped on the Vistula, threatening Cracow. The Prince of Ponte-Corvo commands the Saxon army, camped in front of Dresden, and the Duke of Auerstaedt occupies Bayreuth with eighty thousand French troops. The Duke of Rivoli commands sixty thousand men quartered at Ulm and Donaverth. [General] Oudinot, with the elite corps comprising forty thousand men, is at Augsburg and along the Lech.

The Russians are marching against Austria, and the army [of/in] Friuli today numbers eighty thousand men. Add the Dalmatian corps, without counting the reserves being organized everywhere in the rear, and you see that Austria will be attacked at once on every side. She is consequently hastening toward her ruin. When you receive the order to march, you must not allow yourself to be intimidated by a few troops or a gathering of rabble.

I continue to await news from you with impatience. The Austrians are still at Laybach, Klagenfurth, Villach and Salzburg, and appear to threaten the Tyrol by way of Lintz. Yet one would think that they are considering sending troops into Galicia to oppose the Russians. These dispositions would suggest that their campaign plan has been upset before war has even been declared. There is, however, still nothing definite. The militia have been called into active service, and although efforts have been made to excite people, it has not yet been proved that these levies will provide much reinforcement for the army.

## Row alignment

The literal rows below are direct key output. The French reading applies the explicit editorial interventions in [editorial_interventions.tsv](../inputs/editorial_interventions.tsv). Its character coordinates use uppercase A–Z after removing accents, spaces and punctuation; the unresolved TARGET marker occupies one coordinate (¤). [uncertainties.tsv](../inputs/uncertainties.tsv) retains the contextual key assignments.

### Row 1

Literal: `RENFERMANTLESORDRESETINSTRUCTIONSQUE⟦UNRESOLVED:TARGET⟧MACHARGEDEVOUSDONNERJEMEM`

Editorial French: Renfermant les ordres et instructions que [Sa Majesté] m'a chargé de vous donner. Je m'em

TARGET is unresolved. [Sa Majesté] is a contextual expansion. Spacing, accents and punctuation are editorial.

### Row 2

Literal: `PRESSEAUIOURDHUIDEVOUSDONNESCONNAISSANCEDELAPOSITIONDARMEESFRAN`

Editorial French: presse aujourd'hui de vous donner connaissance de la position d'armées fran

DONNES→DONNER is an editorial repair; I→J in AUIOURDHUI is spelling normalization. The SS and other context-led values in CONNAISSANCE remain proposed key assignments.

### Row 3

Literal: `CAISESETALLIEESLEDUCDEDANZIGALATETEDEQUARANTEMILLEBAVAROIS`

Editorial French: çaises et alliées. Le duc de Danzig à la tête de quarante mille Bavarois

Spacing, accents and punctuation only. The troop strength is a statement in the correspondence.

### Row 4

Literal: `OCCUPEMUNICHEPASSAULEPRINCEPONIATOVVSKIALATETEDETRENTEMILL`

Editorial French: occupe Munich et Passau. Le prince Poniatowski à la tête de trente mille

MUNICHE→MUNICHET adds T; VV→W in Poniatowski normalizes spelling; MILL→MILLE adds E. ARCH_COMPOUND is provisionally empty, with ET retained as an alternative.

### Row 5

Literal: `POLONAISERTCAMPISURLAVISTULEMENACANTCRACOVIELEPRINCEDEPONTE`

Editorial French: Polonais est campé sur la Vistule, menaçant Cracovie. Le prince de Ponte-

ERT→EST and CAMPI→CAMPE are editorial repairs; the literal glyph values remain visible.

### Row 6

Literal: `CORVOCOMMANDELARMEESAXONNECAMPEEENAVANTDEDRESDEETLEDUCDEAUERSTAF`

Editorial French: Corvo commande l'armée saxonne campée en avant de Dresde et le duc d'Auerstaedt

AUERSTAF→AUERSTAEDT restores the historical name. DEAUERSTAF→DAUERSTAEDT also contracts DE before the vowel.

### Row 7

Literal: `OCCUPEBAREUTHAVECQUATREVINGTMILLEFRANCAISETLEDUCDERIUOLICOM`

Editorial French: occupe Bayreuth avec quatre-vingt mille Français et le duc de Rivoli com

BAREUTH→BAYREUTH restores the place name; RIUOLI→RIVOLI normalizes U/V. The compound LE value is contextual.

### Row 8

Literal: `MANDESOIXANTEMILLEHOMMETCANTONNESAULMETDONAVERTHLEGENERAL`

Editorial French: mande soixante mille hommes cantonnés à Ulm et Donaverth. Le [général]

HOMMET→HOMMES is editorial; the key retains q=T. GENERAL is a contextual singleton codeword proposal. Donaverth is retained.

### Row 9

Literal: `OUDINOTAVECLECORPSDEELITEFORMANTQUARANTEMILLEHOMMESESTA`

Editorial French: Oudinot avec le corps d'élite formant quarante mille hommes est à

DEELITE→DELITE contracts the word-sign DE before ELITE. Spacing and punctuation are editorial.

### Row 10

Literal: `AUGSBOURGETSURLELECHLESRUSSESMARCHENTSURLAUTRICHEETLARMEEDE`

Editorial French: Augsbourg et sur le Lech. Les Russes marchent sur l'Autriche et l'armée [du]

FOUR_DOTS=DE is provisional; DANS is an alternative. The reading contracts DE and the next row’s LE to DU across the row boundary.

### Row 11

Literal: `LEFRIOULESTAUJOURDHUIDEQUSTREVINGTMILLEHOMMESAJOUTEZACELA`

Editorial French: Frioul est aujourd'hui de quatre-vingt mille hommes. Ajoutez à cela

QUSTRE→QUATRE is editorial. Initial LE is contracted with DE at the end of row 10 to give DU. The proposed J value is retained in AJOUTEZ.

### Row 12

Literal: `LECORPSDARMEEDEDALMATIE,SANSCOMPRENDRELESRESERVESQTI`

Editorial French: le corps d'armée de Dalmatie, sans comprendre les réserves qui

QTI→QUI is editorial. The quartered-circle sign has a proposed punctuation value.

### Row 13

Literal: `TDERGANISENTDETOURESPARTSSURLESDERRIERESETVOUSVOYEZQUELAUTRICHESERA`

Editorial French: s'organisent de toutes parts sur les derrières et vous voyez que l'Autriche sera

TDERGANISENT→SORGANISENT and TOURES→TOUTES are editorial repairs; the literal values are retained in the decoding.

### Row 14

Literal: `ATTAQUEEALAFOISSURTOURLESPOINTSETELLECOURTPARCONSEQUENTAGRANDS`

Editorial French: attaquée à la fois sur tous les points et elle court par conséquent à grands

TOUR→TOUS is editorial. CONSEQUENT consists of ten visible cleartext letters, not cipher units.

### Row 15

Literal: `PASVERSSAPERTEETVOUSNEDEVEZALORSQUEVOUSRECEVREZORDREDEMARCHERVOUSEN`

Editorial French: pas vers sa perte et vous ne devez, alors que vous recevrez ordre de marcher, vous en

Spacing, accents and punctuation only.

### Row 16

Literal: `LAISSERIMPOSERPARQUELQUESTROUPESOUUNRASSEMBLEMENTDECANAILLES`

Editorial French: laisser imposer par quelques troupes ou un rassemblement de canailles.

RHO is provisionally empty; PAR is also possible. LOW_INWARD_ARCH=S gives plural CANAILLES; an empty value gives singular CANAILLE.

### Row 17

Literal: `JEATTENDSTOUIOURSDEVOSNOUVELLESAVECIMPATIENCE,LESAUTRICHIENSSONT`

Editorial French: J'attends toujours de vos nouvelles avec impatience. Les Autrichiens sont

JEATTENDS→JATTENDS contracts JE; TOUIOURS→TOUJOURS normalizes I/J. Comma versus full stop is editorial.

### Row 18

Literal: `TOUJOURSALAYBACHKLAGENFURTHVILLACHETSALZBURGETSEMBLANT`

Editorial French: toujours à Laybach, Klagenfurth, Villach et Salzburg et semblent

SEMBLANT→SEMBLENT is editorial. Historical place-name spellings are retained.

### Row 19

Literal: `MENACERLETYROLPARLINTZETCEPENDANTONCROIRAITQUEILSSONGENTA`

Editorial French: menacer le Tyrol par Lintz et cependant on croirait qu'ils songent à

QUEILS→QUILS contracts QUE. LINTZ is retained without choosing between a Linz or Lienz interpretation.

### Row 20

Literal: `PORTERDESTROUPESENGALICIEPOURSOPPOSERAUXRUSSESCESDISPOSIONSFE`

Editorial French: porter des troupes en Galicie pour s'opposer aux Russes. Ces dispositions fe

DISPOSIONS→DISPOSITIONS inserts TI editorially. The G in GALICIE is a contextual singleton assignment.

### Row 21

Literal: `RAIENTPRESAGERQUELEURPLANDECAMPAGNEESTDERANGEAVANTQUELAGUERRE`

Editorial French: raient présager que leur plan de campagne est dérangé avant que la guerre

Spacing, accents and punctuation only; the final key includes the proposed reading of the blotted x sign.

### Row 22

Literal: `SOITENCOREDECLAREEETILNEYATOUTEFOISRIENENCOREDEPOSITIFLESMILICES`

Editorial French: soit encore déclarée et il n'y a toutefois rien encore de positif. Les milices

ILNEYAT→ILNYAT contracts NE before Y. RIEN and MILICES include the proposed readings of uncertain stem-circle and blotted-theta signs.

### Row 23

Literal: `SONTMISESENACTIVITEETQUOIQUEONAITCHERCHEAMONTERLESTETES,ILNESTPAS`

Editorial French: sont mises en activité et quoiqu'on ait cherché à monter les têtes, il n'est pas

QUOIQUEON→QUOIQUON contracts QUE. The quartered circle is proposed punctuation; TRIPLEBAR=H gives CHERCHE.

### Row 24

Literal: `ENCOREPROUVEQUECESLEVEESSOYENTDEUNGRANDRENFORTPOURLARMEE`

Editorial French: encore prouvé que ces levées soyent d'un grand renfort pour l'armée.

DEUN→DUN contracts DE. SOYENT is retained as written rather than modernized to SOIENT; accents and punctuation are editorial.
