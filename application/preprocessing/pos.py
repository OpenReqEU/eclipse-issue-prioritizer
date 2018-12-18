# -*- coding: utf-8 -*-

import logging
import nltk
import os
from nltk.tag.stanford import StanfordPOSTagger
from application.util import helper

pos_tagger_dir = os.path.join(helper.APP_PATH, 'postagger')
pos_tagger_jar_path = os.path.join(pos_tagger_dir, 'stanford-postagger.jar')
nltk.data.path = [os.path.join(helper.APP_PATH, "corpora", "nltk_data")]

_logger = logging.getLogger(__name__)


def pos_tagging(requirements, lang="en"):
    """
        POS-Tagging via Stanford POS tagger
        NOTE: This library creates a Java process in the background.
              Please make sure you have installed Java 1.6 or higher.

              sudo apt-get install default-jre
              sudo apt-get install default-jdk
    """

    _logger.info("Pos-tagging for requirements' tokens")

    '''
        See: http://www.comp.leeds.ac.uk/ccalas/tagsets/upenn.html
        --------------------------------------------------------------------------------------------
        Tag    Description                         Examples
        --------------------------------------------------------------------------------------------
        CC     conjunction, coordinating           & 'n and both but either et for less minus neither nor or plus so therefore times v. versus vs. whether yet
        CD     numeral, cardinal                   mid-1890 nine-thirty forty-two one-tenth ten million 0.5 one forty-seven 1987 twenty '79 zero two 78-degrees eighty-four IX '60s .025 fifteen 271,124 dozen quintillion DM2,000 ...
        DT     determiner                          all an another any both del each either every half la many much nary neither no some such that the them these this those
        EX     existential there                   there
        FW     foreign word                        gemeinschaft hund ich jeux habeas Haementeria Herr K'ang-si vous lutihaw alai je jour objets salutaris fille quibusdam pas trop Monte terram fiche oui corporis ...
        IN     preposition or conjunction, subordinating astride among uppon whether out inside pro despite on by throughout below within for towards near behind atop around if like until below next into if beside ...
        JJ     adjective or numeral,ordinal        third ill-mannered pre-war regrettable oiled calamitous first separable ectoplasmic battery-powered participatory fourth still-to-be-named multilingual multi-disciplinary ...
        JJR    adjective, comparative              bleaker braver breezier briefer brighter brisker broader bumper busier calmer cheaper choosier cleaner clearer closer colder commoner costlier cozier creamier crunchier cuter ...
        JJS    adjective, superlative              calmest cheapest choicest classiest cleanest clearest closest commonest corniest costliest crassest creepiest crudest cutest darkest deadliest dearest deepest densest dinkiest ...
        LS     list item marker                    A A. B B. C C. D E F First G H I J K One SP-44001 SP-44002 SP-44005 SP-44007 Second Third Three Two \* a b c d first five four one six three two
        MD     modal auxiliary                     can cannot could couldn't dare may might must need ought shall should shouldn't will would
        NN     noun, common, singular or mass      common-carrier cabbage knuckle-duster Casino afghan shed thermostat investment slide humour falloff slick wind hyena override subhumanity machinist ...
        NNP    noun, proper, singular              Motown Venneboerger Czestochwa Ranzer Conchita Trumplane Christos Oceanside Escobar Kreisler Sawyer Cougar Yvette Ervin ODI Darryl CTCA Shannon A.K.C. Meltex Liverpool ...
        NNPS   noun, proper, plural                Americans Americas Amharas Amityvilles Amusements Anarcho-Syndicalists Andalusians Andes Andruses Angels Animals Anthony Antilles Antiques Apache Apaches Apocrypha ...
        NNS    noun, common, plural                undergraduates scotches bric-a-brac products bodyguards facets coasts divestitures storehouses designs clubs fragrances averages subjectivists apprehensions muses factory-jobs ...
        PDT    pre-determiner                      all both half many quite such sure this
        POS    genitive marker                     ' 's
        PRP    pronoun, personal                   hers herself him himself hisself it itself me myself one oneself ours ourselves ownself self she thee theirs them themselves they thou thy us
        PRP$   pronoun, possessive                 her his mine my our ours their thy your
        RB     adverb                              occasionally unabatingly maddeningly adventurously professedly stirringly prominently technologically magisterially predominately swiftly fiscally pitilessly ...
        RBR    adverb, comparative                 further gloomier grander graver greater grimmer harder harsher healthier heavier higher however larger later leaner lengthier less-perfectly lesser lonelier longer louder lower more ...
        RBS    adverb, superlative                 best biggest bluntest earliest farthest first furthest hardest heartiest highest largest least less most nearest second tightest worst
        RP     particle                            aboard about across along apart around aside at away back before behind by crop down ever fast for forth from go high i.e. in into just later low more off on open out over per pie raising start teeth that through under unto up up-pp upon whole with you
        TO     "to" as preposition or infinitive marker    to
        UH     interjection                        Goodbye Goody Gosh Wow Jeepers Jee-sus Hubba Hey Kee-reist Oops amen huh howdy uh dammit whammo shucks heck anyways whodunnit honey golly man baby diddle hush sonuvabitch ...
        VB     verb, base form                     ask assemble assess assign assume atone attention avoid bake balkanize bank begin behold believe bend benefit bevel beware bless boil bomb boost brace break bring broil brush build ...
        VBD    verb, past tense                    dipped pleaded swiped regummed soaked tidied convened halted registered cushioned exacted snubbed strode aimed adopted belied figgered speculated wore appreciated contemplated ...
        VBG    verb, present participle or gerund  telegraphing stirring focusing angering judging stalling lactating hankerin' alleging veering capping approaching traveling besieging encrypting interrupting erasing wincing ...
        VBN    verb, past participle               multihulled dilapidated aerosolized chaired languished panelized used experimented flourished imitated reunifed factored condensed sheared unsettled primed dubbed desired ...
        VBP    verb, present tense, not 3rd person singular    predominate wrap resort sue twist spill cure lengthen brush terminate appear tend stray glisten obtain comprise detest tease attract emphasize mold postpone sever return wag ...
        VBZ    verb, present tense, 3rd person singular  bases reconstructs marks mixes displeases seals carps weaves snatches slumps stretches authorizes smolders pictures emerges stockpiles seduces fizzes uses bolsters slaps speaks pleads ...
        WDT    WH-determiner                       that what whatever which whichever
        WP     WH-pronoun                          that what whatever whatsoever which who whom whosoever
        WP$    WH-pronoun, possessive              whose
        WRB    Wh-adverb                           how however whence whenever where whereby whereever wherein whereof why

        See: https://www.sketchengine.co.uk/german-stts-part-of-speech-tagset/
        --------------------------------------------------------------------------------------------
        Tag	Description	Example
        --------------------------------------------------------------------------------------------
        ADJA	attributive adjective (including participles used adjectivally)	das große Haus die versunkene Glocke
        ADJD	predicate adjective; adjective used adverbially	der Vogel ist blau er fährt schnell
        ADV	adverb (never used as attributive adjective)	sie kommt bald
        APPR	preposition left hand part of double preposition	auf dem Tisch an der Straße entlang
        APPRART	preposition with fused article	am Tag
        APPO	postposition	meiner Meinung nach
        APZR	right hand part of double preposition	an der Straße entlang
        ART	article (definite or indefinite)	die Tante; eine Tante
        CARD	cardinal number (words or figures); also declined	zwei; 526; dreier
        FM	foreign words (actual part of speech in original language may be appended, e.g. FMADV/ FM-NN)	semper fidem
        ITJ	interjection	Ach!
        KON	co-ordinating conjunction	oder ich bezahle nicht
        KOKOM	comparative conjunction or particle	er arbeitet als Straßenfeger, so gut wie du
        KOUI	preposition used to introduce infinitive clause	um den König zu töten
        KOUS	subordinating conjunction	weil er sie gesehen hat
        NA	adjective used as noun	der Gesandte
        NE	names and other proper nouns	Moskau
        NN	noun (but not adjectives used as nouns)	der Abend
        PAV [PROAV]	pronominal adverb	sie spielt damit
        PAVREL	pronominal adverb used as relative	die Puppe, damit sie spielt
        PDAT	demonstrative determiner	dieser Mann war schlecht
        PDS	demonstrative pronoun	dieser war schlecht
        PIAT	indefinite determiner (whether occurring on its own or in conjunction with another determiner)	einige Wochen, viele solche Bemerkungen
        PIS	indefinite pronoun	sie hat viele gesehen
        PPER	personal pronoun	sie liebt mich
        PRF	reflexive pronoun	ich wasche mich, sie wäscht sich
        PPOSS	possessive pronoun	das ist meins
        PPOSAT	possessive determiner	mein Buch, das ist der meine/meinige
        PRELAT	relative depending on a noun	der Mann, dessen Lied ich singe […], welchen Begriff ich nicht verstehe
        PRELS	relative pronoun (i.e. forms of der or welcher)	der Herr, der gerade kommt; der Herr, welcher nun kommt
        PTKA	particle with adjective or adverb	am besten, zu schnell, aufs herzlichste
        PTKANT	answer particle	ja, nein
        PTKNEG	negative particle	nicht
        PTKREL	indeclinable relative particle	so
        PTKVZ	separable prefix	sie kommt an
        PTKZU	infinitive particle	zu
        PWS	interrogative pronoun	wer kommt?
        PWAT	interrogative determiner	welche Farbe?
        PWAV	interrogative adverb	wann kommst du?
        PWAVREL	interrogative adverb used as relative	der Zaun, worüber sie springt
        PWREL	interrogative pronoun used as relative	etwas, was er sieht
        TRUNC	truncated form of compound	Vor- und Nachteile
        VAFIN	finite auxiliary verb	sie ist gekommen
        VAIMP	imperative of auxiliary	sei still!
        VAINF	infinitive of auxiliary	er wird es gesehen haben
        VAPP	past participle of auxiliary	sie ist es gewesen
        VMFIN	finite modal verb	sie will kommen
        VMINF	infinitive of modal	er hat es sehen müssen
        VMPP	past participle of auxiliary	sie hat es gekonnt
        VVFIN	finite full verb	sie ist gekommen
        VVIMP	imperative of full verb	bleibt da!
        VVINF	infinitive of full verb	er wird es sehen
        VVIZU	infinitive with incorporated zu	sie versprach aufzuhören
        VVPP	past participle of full verb	sie ist gekommen
    '''
    pos_tags_black_list = ['CC', 'CD', 'DT', 'EX', 'IN', 'LS', 'MD', 'PDT', 'POS', 'PRP', 'PRP$', 'RP', 'TO', 'UH', 'VBZ', 'WDT', 'WP', 'WP$', 'WRB']
    #pos_tags_black_list = ['CC', 'CD', 'DT', 'EX', 'LS', 'MD', 'PDT', 'POS', 'PRP', 'PRP$', 'RP', 'TO', 'UH', 'WDT', 'WP', 'WP$', 'WRB']
    existing_stanford_pos_tags = set()
    removed_stanford_tokens = set()
    # Note: "-mx30g" sets java's max memory size to 30 GB RAM
    #       Please change when experiencing OS-related problems!

    if lang == "en":
        pos_tagger_data_path = os.path.join(pos_tagger_dir, 'models', 'english-bidirectional-distsim.tagger')
    elif lang == "de":
        pos_tagger_data_path = os.path.join(pos_tagger_dir, 'models', 'german-ud.tagger')

    pos_tags_black_list = ['CC', 'CD', 'DT', 'EX', 'IN', 'LS', 'MD', 'PDT', 'POS', 'PRP', 'PRP$', 'RP', 'TO', 'UH', 'VBZ', 'WDT', 'WP', 'WP$', 'WRB']
    #pos_tags_black_list = ['CC', 'CD', 'DT', 'EX', 'LS', 'MD', 'PDT', 'POS', 'PRP', 'PRP$', 'RP', 'TO', 'UH', 'WDT', 'WP', 'WP$', 'WRB']
    existing_stanford_pos_tags = set()
    removed_stanford_tokens = set()
    # Note: "-mx30g" sets java's max memory size to 30 GB RAM
    #       Please change when experiencing OS-related problems!
    pos_tagger = StanfordPOSTagger(pos_tagger_data_path, pos_tagger_jar_path, java_options='-mx30g')

    for requirement in requirements:
        pos_tagged_summary_tokens = pos_tagger.tag(requirement.summary_tokens)
        requirement.summary_tokens_pos_tags = list(map(lambda t: t, pos_tagged_summary_tokens))
