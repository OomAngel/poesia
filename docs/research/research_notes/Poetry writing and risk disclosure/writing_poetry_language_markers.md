# Expressive writing, poetry therapy and language markers of suicide risk in writing

Research notes for the PoesIA technical report, written 2026-10-08. Two claims are under test: (1) writing, and poetry in particular, helps people express what they feel more honestly; (2) the language people write carries suicide-risk signals that software could detect, possibly better than conversation.

**How sources were verified.** Every DOI below was resolved against the Crossref REST API (`api.crossref.org/works/<doi>`), and the full author list, year, title, venue, volume and pages come from that record. Findings marked **[abstract]** were read in the PubMed, OpenAlex or Crossref abstract. Findings marked **[full text]** were read in the paper itself (ACL Anthology PDFs for CLPsych 2019 and 2021 and for Shing et al. 2018; Europe PMC full text for Coppersmith et al. 2018). Findings marked **[not seen]** could not be opened and are not reported as verified. Where a "commonly cited" figure comes from memory and was not seen in this session, the notes say so.

---

## Q1. Expressive writing: the core papers, effect sizes, disclosure, and help or harm for people at risk

### Takeaway
Expressive writing has a real but **small** average effect: r = .075 across 146 randomised studies (Frattaroli 2006), roughly d ≈ 0.15. It **does not reliably reduce depressive symptoms** in healthy adults (Reinhold et al. 2018, 39 RCTs). Its best case is PTSD symptoms (SMD −0.43 against waiting list). It reliably raises distress in the short term. In the one trial on people screened for suicidality, it did **not** reduce suicidal thoughts. One RCT found it raised stress during COVID-19. No study measures "honesty of disclosure" as an outcome. The disclosure claim rests on (a) the paradigm's design and (b) a separate literature showing that people report more suicidal ideation in self-administered or written formats than to clinicians (Q3).

### Cited findings

**Pennebaker & Beall 1986 (the founding study)**
- Citation verified: Pennebaker, J. W., & Beall, S. K. (1986). Confronting a traumatic event: Toward an understanding of inhibition and disease. *Journal of Abnormal Psychology, 95*(3), 274–281. https://doi.org/10.1037/0021-843X.95.3.274. Your citation details are correct. — [Crossref](https://doi.org/10.1037/0021-843X.95.3.274); PubMed PMID 3745650 has no abstract — [PubMed](https://pubmed.ncbi.nlm.nih.gov/3745650/)
- **Abstract and full text: not seen** (PsycNET would not load; PubMed has no abstract). Secondary descriptions say healthy undergraduates were assigned to four groups: three wrote about personal traumas (facts only, emotions only, or both) and one wrote about trivial topics, for 15 minutes on 4 consecutive days. Writing about trauma was followed by fewer health-centre visits over the following ~6 months — [Duke Psychiatry blog](https://psychiatry.duke.edu/blog/healing-paper). The commonly cited n = 46 and the finding that the combined emotion-plus-facts condition had *higher* blood pressure and more negative mood right after writing come from memory of the abstract and are not verified here. The Duke blog says blood pressure "dropped", which conflicts with the usual account of this paper; treat that popular claim as unverified.
- Read alongside Smyth (1998), whose synthesis found that writing "increased immediate (pre- to postwriting) distress, which was unrelated to health outcomes" **[abstract]** — [Smyth 1998, PubMed 9489272](https://pubmed.ncbi.nlm.nih.gov/9489272/)

**Smyth 1998**
- Smyth, J. M. (1998). Written emotional expression: Effect sizes, outcome types, and moderating variables. *Journal of Consulting and Clinical Psychology, 66*(1), 174–184. https://doi.org/10.1037/0022-006X.66.1.174 — [Crossref](https://doi.org/10.1037/0022-006X.66.1.174)
- In healthy participants, writing improved reported physical health, psychological well-being, physiological functioning and general functioning, but **not health behaviours**. Moderators included student samples, gender, duration, publication status and writing instructions **[abstract]** — [PubMed](https://pubmed.ncbi.nlm.nih.gov/9489272/)
- The widely quoted overall **d = .47 (13 studies)** is not in the abstract and was not seen; treat it as unverified. Frattaroli (2006) notes that Smyth used a **fixed-effects** model, which limits how far it generalises **[abstract]** — [PubMed 17073523](https://pubmed.ncbi.nlm.nih.gov/17073523/)

**Frattaroli 2006**
- Frattaroli, J. (2006). Experimental disclosure and its moderators: A meta-analysis. *Psychological Bulletin, 132*(6), 823–865. https://doi.org/10.1037/0033-2909.132.6.823. Your details are correct. — [Crossref](https://doi.org/10.1037/0033-2909.132.6.823)
- **146 randomised studies**; the random-effects average is **r = .075**, positive and significant, with several moderators **[abstract]** — [PubMed](https://pubmed.ncbi.nlm.nih.gov/17073523/). Converted, r = .075 ≈ d = 0.15, a small effect (my conversion, d = 2r/√(1−r²)). Note that the paper covers "experimental disclosure" (written *and* spoken), not writing alone.

**Reinhold, Bürkner & Holling 2018 (depression)**
- Reinhold, M., Bürkner, P.-C., & Holling, H. (2018). Effects of expressive writing on depressive symptoms—A meta-analysis. *Clinical Psychology: Science and Practice, 25*(1), e12224. https://doi.org/10.1111/cpsp.12224 — [Crossref](https://doi.org/10.1111/cpsp.12224)
- Physically healthy adults with varying stress and **without PTSD**: **39 RCTs, 64 intervention–control comparisons**. "Expressive writing did not yield significant long-term effects on depressive symptoms." Effects were larger with more sessions and more specific topics. The authors conclude the results "did not support the effectiveness of brief, self-directed expressive writing as an intervention that decreases depressive symptoms" **[abstract via OpenAlex]** — [OpenAlex record](https://api.openalex.org/works/doi:10.1111/cpsp.12224)
- The exact pooled g (often quoted as about −0.09, non-significant) was **not seen**.

**Pavlacic et al. 2019 (PTSD, growth, quality of life)**
- Pavlacic, J. M., Buchanan, E. M., Maxwell, N. P., Hopke, T. G., & Schulenberg, S. E. (2019). A meta-analysis of expressive writing on posttraumatic stress, posttraumatic growth, and quality of life. *Review of General Psychology, 23*(2), 230–250. https://doi.org/10.1177/1089268019831645 — [Crossref](https://doi.org/10.1177/1089268019831645)
- **Correction to how it is usually cited:** this meta-analysis pooled **pre–post change within the expressive-writing groups only**, not writing against control. It found a **small** effect for posttraumatic stress, negligible-to-small effects for posttraumatic growth and quality of life, and a medium-to-large effect only in studies that required a PTSD diagnosis **[abstract via Crossref]** — [Crossref](https://doi.org/10.1177/1089268019831645). Within-group effects include regression to the mean and the passage of time, so they cannot be read as treatment efficacy.

**Gerger et al. 2021/2022 (network meta-analysis, trauma survivors)**
- Gerger, H., Werner, C. P., Gaab, J., & Cuijpers, P. (2022). Comparative efficacy and acceptability of expressive writing treatments compared with psychotherapy, other writing treatments, and waiting list control for adult trauma survivors: a systematic review and network meta-analysis. *Psychological Medicine, 52*(15), 3484–3496 (online 2021). https://doi.org/10.1017/S0033291721000143 — [Crossref](https://doi.org/10.1017/S0033291721000143)
- **44 RCTs, 7,724 participants.** SMDs against waiting list at longest follow-up: PTSD psychotherapy −0.78; enhanced writing −0.81; **expressive writing −0.43 (−0.65 to −0.21)**; **neutral writing −0.37 (−0.61 to −0.14)**. Heterogeneity was considerable and every study had elevated risk of bias in at least one dimension **[abstract]** — [PubMed 33634766](https://pubmed.ncbi.nlm.nih.gov/33634766/). Neutral writing nearly matching expressive writing is a caution: part of the benefit may be non-specific.

**Adverse effects and people at risk**
- Kovac, S. H., & Range, L. M. (2002). Does writing about suicidal thoughts and feelings reduce them? *Suicide and Life-Threatening Behavior, 32*(4), 428–440. https://doi.org/10.1521/suli.32.4.428.22335. Design: **121 undergraduates screened for suicidality**, 20 minutes on 4 days over 2 weeks, randomised to cognitive reinterpretation, exposure (write and rewrite trauma), or innocuous topics. Completers: **N = 98**. The groups did **not differ on suicidality or depression** at post or at 6-week follow-up. All groups reported fewer automatic negative thoughts and higher self-regard, **but more health-centre visits** at follow-up. Authors: "Suicidal thoughts may be more resistant than physical health to writing interventions" **[abstract]** — [PubMed 12501967](https://pubmed.ncbi.nlm.nih.gov/12501967/)
- Vukčević Marković, M., Bjekić, J., & Priebe, S. (2020). Effectiveness of expressive writing in the reduction of psychological distress during the COVID-19 pandemic: A randomized controlled trial. *Frontiers in Psychology, 11*, 587282. https://doi.org/10.3389/fpsyg.2020.587282. **n = 120**, online, 5 sessions over 2 weeks against treatment as usual. **A less favourable outcome on psychological distress and stress in the writing group** after baseline adjustment; no group differences at 1-month follow-up. Authors: EW "may be harmful" in that context **[abstract]** — [PubMed 33240180](https://pubmed.ncbi.nlm.nih.gov/33240180/)
- Gortner, E.-M., Rude, S. S., & Pennebaker, J. W. (2006). Benefits of expressive writing in lowering rumination and depressive symptoms. *Behavior Therapy, 37*(3), 292–303. https://doi.org/10.1016/j.beth.2006.01.004. In depression-vulnerable students, benefit appeared **only in those high in emotional suppression** (lower depression at 6 months), and it was mediated by less brooding. A booster session added nothing **[abstract]** — [PubMed 16942980](https://pubmed.ncbi.nlm.nih.gov/16942980/)
- Baikie, K. A., & Wilhelm, K. (2005). Emotional and physical health benefits of expressive writing. *Advances in Psychiatric Treatment, 11*(5), 338–346. https://doi.org/10.1192/apt.11.5.338. This is a narrative review describing the paradigm (15–20 minutes on 3–5 occasions) and its use in clinical populations **[abstract via OpenAlex]** — [OpenAlex](https://api.openalex.org/works/doi:10.1192/apt.11.5.338)

### Inferences
- The defensible wording for PoesIA is that structured emotional writing has a **small, heterogeneous** benefit on average. It does not reliably reduce depression in non-clinical adults and has the strongest evidence for trauma symptoms. It should not be described as a treatment.
- **Short-term distress is an expected effect of the paradigm** (Smyth 1998). For an app whose users may include people at risk, this supports keeping a safety pause and post-writing grounding. The only RCT in screened-suicidal students (Kovac & Range 2002) found no reduction in suicidality, and the COVID RCT found more stress.
- No meta-analysis here measured whether writing makes people disclose *more honestly*. "Writing increases disclosure" is a premise of the paradigm, not a tested outcome. The nearest empirical support is the self-report versus clinician-interview literature (Q3).

### Gaps
- Pennebaker & Beall's abstract and full text were not seen. Pin n, conditions and the blood-pressure direction from the PDF before quoting them.
- Smyth's d = .47 and Reinhold's pooled g were not seen.
- No systematic review of **adverse events** in expressive writing was found (the PubMed search "expressive writing AND (adverse OR harm*) AND meta-analysis" returned nothing relevant). Harms are reported only trial by trial.
- No study was found that compares the honesty or completeness of disclosure in writing with disclosure in speech using an outcome criterion.

---

## Q2. Poetry therapy and creative-writing interventions: systematic reviews and evidence quality

### Takeaway
The best current synthesis of poetry specifically (Kassab et al., Psychiatry Research 2026) finds moderate-to-large pooled effects on PTSD, depression, anxiety and stress. But it rests on **15 small, mostly high-risk-of-bias studies** (RCTs, case-control and pre–post designs), with signs of publication bias. The authors recommend poetry only as an **adjunct** until preregistered RCTs exist. For creative writing generally, a 2024 meta-analysis (Porras-Segovia et al.) found that narrative writing reduces depression compared with neutral writing or treatment as usual, but **too few studies on suicidal ideation existed to meta-analyse**. No study tests whether *poetry*, as distinct from prose, increases honest emotional disclosure.

### Cited findings
- Kassab, A., Jayatunge, R., & Bou Khalil, R. (2026). The therapeutic functions of poetry in mental health: A systematic review and meta-analysis. *Psychiatry Research, 356*, 116897. https://doi.org/10.1016/j.psychres.2025.116897. Searched PubMed and Google Scholar to November 2023, English or French studies. **15 studies (RCT, case-control, pre–post)**; only those scoring ≥6 on the Newcastle-Ottawa Scale entered the meta-analysis. Results: "large reductions in PTSD symptoms and significant improvements in depressive symptoms, anxiety, and stress, with effect sizes generally in the moderate-to-large range"; resilience non-significant and imprecise; no reliable benefit for pain, with small-study effects. "Most trials were small, at risk of bias, and methodologically heterogeneous… High-quality, preregistered randomized controlled trials are needed before poetry-based interventions can be firmly recommended beyond an adjunctive role" **[abstract]** — [PubMed 41411711](https://pubmed.ncbi.nlm.nih.gov/41411711/). The pooled SMD values were not seen; the abstract gives only verbal magnitudes. It searched only two databases, which is thin for a systematic review.
- Porras-Segovia, A., Escobedo-Aedo, P. J., Carrillo de Albornoz, C. M., Guerrero-Jiménez, M., Lis, L., Molina-Madueño, R., Gutiérrez-Rojas, L., & Alacreu-Crespo, A. (2024). Writing to keep on living: A systematic review and meta-analysis on creative writing therapy for the management of depression and suicidal ideation. *Current Psychiatry Reports, 26*(7), 359–378. https://doi.org/10.1007/s11920-024-01511-6. 21 of 31 studies showed improved depressive symptoms. In meta-analysis, **narrative writing significantly reduced depression compared with neutral writing or treatment as usual, at post-intervention and follow-up**. "The number of studies exploring the effects of creative writing in suicidal ideation was too low to perform a meta-analysis" **[abstract]** — [PubMed 38717657](https://pubmed.ncbi.nlm.nih.gov/38717657/). This is a Spanish group, relevant for the Spanish-language arm. Its "creative writing" category includes expressive and narrative writing, so it is not poetry-specific.
- Mundy, S. S., Kudahl, B., Bundesen, B., Hellström, L., Rosenbaum, B., & Eplov, L. F. (2022). Mental health recovery and creative writing groups: A systematic review. *Nordic Journal of Arts, Culture and Health, 4*(1), 1–18. https://doi.org/10.18261/njach.4.1.1. Of **7,743 records, 6 studies were included (2 quantitative, 4 qualitative)**. Only one measured clinical recovery (depression fell from moderate to mild, pre–post). Possible gains in connectedness, empowerment and identity (CHIME framework). Evidence is "scarce, heterogeneous, and with methodological limitations" **[abstract via OpenAlex]** — [OpenAlex](https://api.openalex.org/works/doi:10.18261/njach.4.1.1)
- Heimes, S. (2011). State of poetry therapy research (review). *The Arts in Psychotherapy, 38*(1), 1–8. https://doi.org/10.1016/j.aip.2010.09.006. Metadata verified on Crossref; **abstract and full text not seen** (ScienceDirect returned 403; no abstract in Crossref, OpenAlex or Semantic Scholar). Do not report its findings as verified — [Crossref](https://doi.org/10.1016/j.aip.2010.09.006)
- Other poetry reviews found but outside the PoesIA population: poetry interventions in dementia care (scoping review, 6 studies) — [PubMed 39961313](https://pubmed.ncbi.nlm.nih.gov/39961313/); poetry and empathy or burnout in health workers (systematic review, 6 items, only one poetry-only) — [PubMed 31354038](https://pubmed.ncbi.nlm.nih.gov/31354038/)
- Background on poets and risk: Kaufman, J. C. (2001). The Sylvia Plath effect: Mental illness in eminent creative writers. *The Journal of Creative Behavior, 35*(1), 37–50. https://doi.org/10.1002/j.2162-6057.2001.tb01220.x. Among **1,629 writers**, female poets were significantly more likely to have had mental illness than female fiction writers or male writers. A second sample of **520 eminent women** replicated the finding for poets **[abstract via Crossref]** — [Crossref](https://doi.org/10.1002/j.2162-6057.2001.tb01220.x). These are historical and biographical data on eminent writers, not a population base rate.

### Inferences
- Claim (1) holds only in a weak form. Writing and poetry interventions are associated with symptom improvement in small, biased trials. **None of these reviews measured disclosure honesty**, and none compared poetry with prose expressive writing head to head. "Poetry helps people express what they feel more honestly" is therefore a hypothesis grounded in practice and theory, not an evidenced finding. The report should say this plainly.
- Kassab et al. pooled reading, writing and discussing poems. PoesIA is solo writing that an AI assists, which no review covers.
- Kaufman (2001) suggests a poetry app may draw users with above-average psychological vulnerability. That is an argument for the safety pause, not against the app (an inference from biographical data).

### Gaps
- No Cochrane or Campbell review of poetry therapy or creative writing for mental health was found.
- Heimes (2011) was not seen.
- No RCT compares poetry writing with prose expressive writing.
- No study measures emotional disclosure (depth, honesty, self-concealment) as the outcome of a poetry intervention.

---

## Q3. Language markers of suicide risk in writing: what was found, how well classifiers perform, how they generalise, and how they compare with clinicians

### Takeaway
There are real, replicated but **small** linguistic correlates of distress. First-person singular "I-talk" correlates with depression at r ≈ .10–.13, and Tackman et al. (2019) show this largely reflects general negative emotionality rather than depression or suicidality specifically. The poetry study everyone cites (Stirman & Pennebaker 2001) is **18 poets** and ~300 poems.

Text classifiers look strong on **balanced, retrospective, case-control** data:
- AUC ~0.89–0.93 and 70–85% TPR at 10% FPR on 1:1 matched Twitter users (Coppersmith et al. 2018);
- urgent-risk F1 ~0.84 on Reddit (CLPsych 2019).

They are much weaker when the labels are clinically meaningful and the evaluation is honest:
- CLPsych 2021 (real self-reported attempts, test sets of 22–30 users): best 30-day AUC ≈ 0.74, and only one team beat a bag-of-words baseline on F1;
- Facebook posts against validated questionnaires: AUC 0.62–0.75.

Models transfer poorly across platforms (Harrigian et al. 2020). At realistic base rates the positive predictive value collapses to single digits (Belsher et al. 2019: PPV ≤ 0.01 for suicide death in most models).

The "better than conversation" claim has partial support:
- patients disclose more suicidal ideation on written or self-report instruments than in clinician interviews;
- in one study, machine classification of suicide notes beat clinicians (78% vs 63%), but on a genuine-versus-simulated-notes task, not a prediction task;
- no prospective head-to-head of text classifiers against clinician assessment was found.

### Cited findings

**Stirman & Pennebaker 2001 (poetry): what was actually measured**
- Citation (corrected author form): Wiltsey Stirman, S., & Pennebaker, J. W. (2001). Word use in the poetry of suicidal and nonsuicidal poets. *Psychosomatic Medicine, 63*(4), 517–522. https://doi.org/10.1097/00006842-200107000-00001. The first author is Shannon Wiltsey Stirman, indexed as "Wiltsey Stirman" (Crossref) and as "Stirman SW" in PubMed. — [Crossref](https://doi.org/10.1097/00006842-200107000-00001)
- **Design and n:** "Approximately 300 poems from the early, middle, and late periods of **nine suicidal poets and nine nonsuicidal poets**" analysed with LIWC to test two suicide models. **Finding:** suicidal poets used "more words pertaining to the individual self and fewer words pertaining to the collective" (I versus we). For communication words, only "the direction of effects… was consistent with the social integration model", i.e. not presented as a clear significant effect **[abstract]** — [PubMed 11485104](https://pubmed.ncbi.nlm.nih.gov/11485104/)
- **How it is popularly cited, and the correction:** it is often cited as showing that suicidal poets used more negative-emotion or death words, or that software "can predict suicide from poems". The abstract reports **only** the self/collective pronoun finding and a directional communication-word result. The unit is 18 poets (famous, historical, chosen retrospectively), so no classifier, no out-of-sample test and no prospective prediction. Its last sentence ("linguistic predictors of suicide can be discerned") is a hypothesis-level claim. Emotion and death-word results were not seen (full text not opened).

**The I-talk literature that frames how big this signal is**
- Tackman, A. M., Sbarra, D. A., Carey, A. L., Donnellan, M. B., Horn, A. B., Holtzman, N. S., Edwards, T. S., Pennebaker, J. W., & Mehl, M. R. (2019). Depression, negative emotionality, and self-referential language: A multi-lab, multi-measure, and multi-language-task research synthesis. *Journal of Personality and Social Psychology, 116*(5), 817–834. https://doi.org/10.1037/pspp0000187. Preregistered, **N = 4,754**, 6 labs, 2 countries: depression–I-talk **r = .10 [.07, .13]**. The effect largely reflects **negative emotionality**, so I-talk is "a linguistic marker of general distress proneness… rather than… a specific marker of depression"; it was absent in impersonal writing contexts **[abstract]** — [PubMed 29504797](https://pubmed.ncbi.nlm.nih.gov/29504797/)
- Edwards, T., & Holtzman, N. S. (2017). A meta-analysis of correlations between depression and first person singular pronoun use. *Journal of Research in Personality, 68*, 63–68. https://doi.org/10.1016/j.jrp.2017.02.005. Metadata verified; **abstract not seen**. The commonly cited r ≈ .13 is unverified here — [Crossref](https://doi.org/10.1016/j.jrp.2017.02.005)
- Rude, S., Gortner, E.-M., & Pennebaker, J. (2004). Language use of depressed and depression-vulnerable college students. *Cognition & Emotion, 18*(8), 1121–1133. https://doi.org/10.1080/02699930441000030. Currently depressed students used more negative words and more "I" in essays; formerly depressed students differed only late in the essay **[abstract]** — [OpenAlex](https://api.openalex.org/works/doi:10.1080/02699930441000030)

**Suicide notes**
- Pestian, J., Nasrallah, H., Matykiewicz, P., Bennett, A., & Leenaars, A. (2010). Suicide note classification using natural language processing: A content analysis. *Biomedical Informatics Insights, 3*, 19–28 (article BII.S4706). https://doi.org/10.4137/BII.S4706. **33 genuine notes from people who died by suicide** against **33 notes elicited from healthy controls**. **11 mental health professionals: 63% correct; 31 psychiatry trainees: 49%; best ML algorithm: 78%** **[abstract]** — [PubMed 21643548](https://pubmed.ncbi.nlm.nih.gov/21643548/). This is the cleanest "machine beats clinicians on text" result, but the task is *genuine versus simulated note*, n = 66, with no prospective risk prediction.
- Pestian, J. P., Matykiewicz, P., Linn-Gust, M., South, B., Uzuner, O., Wiebe, J., Cohen, K. B., Hurdle, J., & Brew, C. (2012). Sentiment analysis of suicide notes: A shared task. *Biomedical Informatics Insights, 5*(Suppl. 1), 3–16. https://doi.org/10.4137/BII.S9042. Emotion labelling of notes; "many systems performed at levels approaching the inter-coder agreement" **[abstract via OpenAlex]** — [OpenAlex](https://api.openalex.org/works/doi:10.4137/BII.S9042). Corpus size and F1 were not seen.
- Handelman, L. D., & Lester, D. (2007). The content of suicide notes from attempters and completers. *Crisis, 28*(2), 102–104. https://doi.org/10.1027/0227-5910.28.2.102. In LIWC, notes from completed suicides had **fewer metaphysical references, more future-tense verbs, more social references and more positive emotion** than notes from attempters **[abstract]** — [PubMed 17722692](https://pubmed.ncbi.nlm.nih.gov/17722692/). This is counter-intuitive: positive emotion is not a safety signal.
- Spanish: García-Caballero, A., Jiménez, J., Fernández-Cabana, M., & García-Lado, I. (2012). P-1419 – Last words: An LIWC analysis of suicide notes from Spain. *European Psychiatry, 27*(Suppl. 1), 1. https://doi.org/10.1016/S0924-9338(12)75586-4. A conference abstract: **23 notes** from Ourense (2006–2010; 144 suicides), with gender, age and rural/urban differences in LIWC categories **[abstract via OpenAlex]** — [OpenAlex](https://api.openalex.org/works/doi:10.1016/s0924-9338(12)75586-4). This is descriptive only; it has no classifier.

**Spoken language (for contrast with writing)**
- Pestian, J. P., Sorter, M., Connolly, B., Bretonnel Cohen, K., McCullumsmith, C., Gee, J. T., Morency, L.-P., Scherer, S., Rohlfs, L., & the STM Research Group (2017). A machine learning approach to identifying the thought markers of suicidal subjects: A prospective multicenter trial. *Suicide and Life-Threatening Behavior, 47*(1), 112–121 (online 2016). https://doi.org/10.1111/sltb.12312. **379 subjects** at three sites; words plus acoustics from interviews; three-way classification (suicidal / mentally ill not suicidal / control) **up to 85% accuracy** **[abstract]** — [PubMed 27813129](https://pubmed.ncbi.nlm.nih.gov/27813129/). "Prospective" refers to recruitment, not to predicting future attempts. The data are speech, not writing.

**Social media and prediction**
- Coppersmith, G., Leary, R., Crutchley, P., & Fine, A. (2018). Natural language processing of social media as screening for suicide risk. *Biomedical Informatics Insights, 10*, 1178222618792860. https://doi.org/10.1177/1178222618792860 — [Crossref](https://doi.org/10.1177/1178222618792860)
  - Data **[full text]**: 186 suicide-attempt survivors who donated data via OurDataHelps.org plus people who publicly self-stated attempts on social media; combined **547 attempters, 418 with a known attempt month (263 with an exact date)**; each matched 1:1 to a control by gender and approximate age. Six-month window: 197,615 posts from attempters plus 197,615 from controls.
  - Evaluation **[full text]**: 10-fold cross-validation across matched pairs. "At 10% false alarm rate… the models… range from **70% to 85% true positive rate**" — [Europe PMC full text](https://europepmc.org/article/PMC/PMC6111391)
  - AUCs (in the figure legend, not seen directly) are reported by MacAvaney et al. (2021) as **.89 using tweets 30 days before an attempt and .93 using six months** **[full text of MacAvaney et al.]** — [ACL Anthology](https://aclanthology.org/2021.clpsych-1.7/)
  - Limits: the 1:1 case-control design means 50% prevalence in evaluation; the self-stated cohort is people who talk publicly about attempts; the sample is mostly women aged 18–24 **[full text]**.
- Ophir, Y., Tikochinski, R., Asterhan, C. S. C., Sisso, I., & Reichart, R. (2020). Deep neural networks detect suicide risk from textual Facebook posts. *Scientific Reports, 10*(1), 16685. https://doi.org/10.1038/s41598-020-73917-0. **1,002 authenticated users, 83,292 posts**, with labels from validated psychosocial questionnaires (not proxies). Direct text→suicide model **AUC 0.621–0.629**; the multi-task model through personality, psychosocial risk and disorder reached **AUC 0.697–0.746**. Predictions "did not rely on explicit suicide-related themes". The paper frames 50 years of research as AUC 0.56–0.58 **[abstract]** — [PubMed 33028921](https://pubmed.ncbi.nlm.nih.gov/33028921/). This is the most realistic everyday-text benchmark found: modest discrimination.
- Spanish Twitter: García-Martínez, C., Oliván-Blázquez, B., Fabra, J., Martínez-Martínez, A. B., Pérez-Yus, M. C., & López-Del-Hoyo, Y. (2022). Exploring the risk of suicide in real time on Spanish Twitter: Observational study. *JMIR Public Health and Surveillance, 8*(5), e31800. https://doi.org/10.2196/31800. Of **2,509 lexicon-filtered tweets, 8.61% (n = 216)** were judged suicidal by most of 3 experts per tweet. Severity correlated with sadness (ρ = .266) and negatively with joy (ρ = −.234), and was higher with defeat, desire to escape, low support and helplessness **[abstract]** — [PubMed 35579921](https://pubmed.ncbi.nlm.nih.gov/35579921/). This is a correlational study, not a classifier.

**CLPsych shared tasks**
- **2018 dataset paper:** Shing, H.-C., Nair, S., Zirikly, A., Friedenberg, M., Daumé III, H., & Resnik, P. (2018). Expert, crowdsourced, and machine assessment of suicide risk via online postings. *Proceedings of the Fifth Workshop on Computational Linguistics and Clinical Psychology (CLPsych 2018)*, 25–36. https://doi.org/10.18653/v1/W18-0603. Four-level user risk (none / low / moderate / severe) from r/SuicideWatch posts; **245 users** labelled by 4 experts and **865 users** by crowdworkers. Crowd Krippendorff's α = 0.554. Macro-F1 against all-expert consensus: long-instruction experts 0.837, short-instruction experts 0.717, **CrowdFlower 0.505**. Crowdworkers tended to under-call severe users **[full text]** — [ACL Anthology](https://aclanthology.org/W18-0603/)
- **2019:** Zirikly, A., Resnik, P., Uzuner, Ö., & Hollingshead, K. (2019). CLPsych 2019 shared task: Predicting the degree of suicide risk in Reddit posts. *Proceedings of the Sixth Workshop on Computational Linguistics and Clinical Psychology*, 24–33. https://doi.org/10.18653/v1/W19-3003 **[full text]** — [ACL Anthology](https://aclanthology.org/W19-3003/)
  - Labels: expert α = **0.81** and crowd α = **0.55** on the same four-level scale (crowd consensus labels were used for the task data).
  - Users: 621 risk-labelled users (a/b/c/d = 159/63/141/258) plus 621 controls, total 1,242 (test 249).
  - Tasks: A = risk from SuicideWatch posts; B = SuicideWatch plus all of the user's other posts; C = screening from **non**-mental-health posts only. 15 teams.
  - Best official **macro-F1: A 0.481** (best unofficial 0.533), **B 0.457** (unofficial 0.504), **C 0.268** (unofficial 0.278).
  - On task A the binary "flagged" F1 reached up to 0.922 and "urgent" (c+d vs a+b) up to 0.862; the per-class F1 for low risk (b) was ≤0.32.
  - Systems over-predicted severe when the truth was moderate; some false positives were people seeking help for a friend.
- **2021:** MacAvaney, S., Mittu, A., Coppersmith, G., Leintz, J., & Resnik, P. (2021). Community-level research on suicidality prediction in a secure environment: Overview of the CLPsych 2021 shared task. *Proceedings of the Seventh Workshop on Computational Linguistics and Clinical Psychology: Improving Access*, 70–80. https://doi.org/10.18653/v1/2021.clpsych-1.7. **Correction to your citation:** the second author is **Mittu** (Anjali), not "Mittal", and the first author is spelled MacAvaney — [Crossref](https://doi.org/10.18653/v1/2021.clpsych-1.7)
  - Data **[full text]**: donated OurDataHelps Twitter data with **self-reported attempt dates**, run in a NORC secure data enclave. Of 3,631 donors (1,613 attempters), filtering left 250 dated attempters. Subtask 1 used 68 attempters with tweets in the 30 days before the attempt; subtask 2 used 97 with tweets in the prior 6 months. Each was matched 1:1 to a control by gender, age within 5 years and tweet volume.
  - Users in train/test: subtask 1 = **114 / 22**; subtask 2 = **164 / 30**. Most users were women aged 18–24. 21 teams signed up and **5 submitted**.
  - Results, 30-day window **[full text]**: logistic-regression n-gram baseline F1 0.636 / AUC 0.661. Best F1 0.692 (UlyaLamia; TPR 0.818, false-alarm rate 0.545). Best AUC 0.740. **Only one team beat the baseline F1.**
  - Results, 6-month window **[full text]**: baseline F1 0.710 / AUC 0.764. Best ScyLab (LIWC/dictionary Bayesian logistic regression) **F1 0.815, AUC 0.844, false-alarm rate 0.067**. The paper's conclusion says "up to 0.823 F1", while Table 4's maximum is 0.815, a small inconsistency within the paper.
  - Ranking plots show that some attempters were missed by nearly all systems.
- **2022 and 2024 (metadata verified, content not read):**
  - Tsakalidis, A., Chim, J., Bilal, I. M., Zirikly, A., Atzil-Slonim, D., Nanni, F., Resnik, P., Gaur, M., Roy, K., Inkster, B., Leintz, J., & Liakata, M. (2022). Overview of the CLPsych 2022 shared task: Capturing moments of change in longitudinal user posts. *Proc. Eighth CLPsych Workshop*, 184–198. https://doi.org/10.18653/v1/2022.clpsych-1.16
  - Chim, J., Tsakalidis, A., Gkoumas, D., Atzil-Slonim, D., Ophir, Y., Zirikly, A., Resnik, P., & Liakata, M. (2024). Overview of the CLPsych 2024 shared task: Leveraging large language models to identify evidence of suicidality risk in online posts. *Proc. 9th CLPsych Workshop*, 177–190. https://doi.org/10.18653/v1/2024.clpsych-1.15
  - Findings of both: **not seen**.

**Generalisation and validity**
- Harrigian, K., Aguirre, C., & Dredze, M. (2020). Do models of mental health based on social media data generalize? *Findings of the Association for Computational Linguistics: EMNLP 2020*, 3774–3788. https://doi.org/10.18653/v1/2020.findings-emnlp.337. Depression classifiers suffer "substantial loss… when transferring between platforms", and confounds can make researchers overestimate performance **[abstract via OpenAlex]** — [OpenAlex](https://api.openalex.org/works/doi:10.18653/v1/2020.findings-emnlp.337)
- Chancellor, S., & De Choudhury, M. (2020). Methods in predictive techniques for mental health status on social media: a critical review. *npj Digital Medicine, 3*(1), 43. https://doi.org/10.1038/s41746-020-0233-7. 75 studies (2013–2018) show "concerning trends around construct validity" in how mental-health status is labelled **[abstract]** — [PubMed 32219184](https://pubmed.ncbi.nlm.nih.gov/32219184/)
- Bernert, R. A., Hilberg, A. M., Melia, R., Kim, J. P., Shah, N. H., & Abnousi, F. (2020). Artificial intelligence and suicide prevention: A systematic review of machine learning investigations. *International Journal of Environmental Research and Public Health, 17*(16), 5929. https://doi.org/10.3390/ijerph17165929. **87 studies**, with reported accuracy and AUC often >90%, but methods varied widely **[abstract]** — [PubMed 32824149](https://pubmed.ncbi.nlm.nih.gov/32824149/). High reported accuracy is largely an artefact of balanced and retrospective designs.

**Base rates and PPV**
- Belsher, B. E., Smolenski, D. J., Pruitt, L. D., Bush, N. E., Beech, E. H., Workman, D. E., Morgan, R. L., Evatt, D. P., Tucker, J., & Skopp, N. A. (2019). Prediction models for suicide attempts and deaths: A systematic review and simulation. *JAMA Psychiatry, 76*(6), 642–651. https://doi.org/10.1001/jamapsychiatry.2019.0174. **17 cohort studies, 64 models, >14 million participants**, mostly health-record models rather than text. Global classification accuracy was good (≥0.80 in most), but **PPV for suicide death was ≤0.01 in most models**; simulations show very low PPV across settings; "their accuracy of predicting a future event is near 0" **[abstract]** — [PubMed 30865249](https://pubmed.ncbi.nlm.nih.gov/30865249/)
- Franklin, J. C., Ribeiro, J. D., Fox, K. R., Bentley, K. H., Kleiman, E. M., Huang, X., Musacchio, K. M., Jaroszewski, A. C., Chang, B. P., & Nock, M. K. (2017). Risk factors for suicidal thoughts and behaviors: A meta-analysis of 50 years of research. *Psychological Bulletin, 143*(2), 187–232. https://doi.org/10.1037/bul0000084. **365 studies, 3,428 effect sizes**: prediction was "only slightly better than chance" for all outcomes and has not improved in 50 years **[abstract]** — [PubMed 27841450](https://pubmed.ncbi.nlm.nih.gov/27841450/)

**Writing or self-report against conversation with a clinician (the "better than conversation" claim)**
- Greist, J. H., Laughren, T. P., Gustafson, D. H., Stauss, F. F., Rowse, G. L., & Chiles, J. A. (1973). A computer interview for suicide-risk prediction. *American Journal of Psychiatry, 130*(12), 1327–1332. https://doi.org/10.1176/ajp.130.12.1327. **22 patients**; patients **preferred the computer interview to talking to a physician**; in a separate retrospective study **the computer was more accurate than clinicians** in predicting attempts **[abstract via OpenAlex]** — [OpenAlex](https://api.openalex.org/works/doi:10.1176/ajp.130.12.1327). The study is tiny and old.
- Vera-Varela, C., Manrique Mirón, P. C., Barrigón, M. L., Álvarez-García, R., Portillo, P., Chamorro, J., MEmind Study Group, & Baca-García, E. (2022). Low level of agreement between self-report and clinical assessment of passive suicidal ideation. *Archives of Suicide Research, 26*(4), 1895–1910. https://doi.org/10.1080/13811118.2021.1945984. **648 Spanish outpatients**: **kappa = 0.072**; in **56.4% (n = 366)** the clinician recorded no death-related ideas while the patient, within 24 hours, self-reported no desire to live **[abstract]** — [PubMed 34223799](https://pubmed.ncbi.nlm.nih.gov/34223799/)
- Gao, K., Wu, R., Wang, Z., Ren, M., Kemp, D. E., Chan, P. K., Conroy, C. M., Serrano, M. B., Ganocy, S. J., & Calabrese, J. R. (2015). Disagreement between self-reported and clinician-ascertained suicidal ideation and its correlation with depression and anxiety severity in patients with major depressive disorder or bipolar disorder. *Journal of Psychiatric Research, 60*, 117–124. https://doi.org/10.1016/j.jpsychires.2014.09.011. MDD (n = 103): **5.8% clinician-ascertained versus 22.4% self-reported** suicidal ideation. Bipolar disorder (n = 147): 18.4% versus 35.9%. Kappa 0.30 and 0.43 **[abstract]** — [PubMed 25438963](https://pubmed.ncbi.nlm.nih.gov/25438963/)
- Nobile, B., Gourguechon-Buot, E., Gorwood, P., Olié, E., & Courtet, P. (2024). Association of clinical characteristics, depression remission and suicide risk with discrepancies between self- and clinician-rated suicidal ideation: Two large naturalistic cohorts of outpatients with depression. *Psychiatry Research, 335*, 115833. https://doi.org/10.1016/j.psychres.2024.115833. **Discordant suicidal ideation in 49.3% and 34% of patients** in two French cohorts. **Self- and clinician ratings predicted suicide attempts comparably** **[abstract]** — [PubMed 38471242](https://pubmed.ncbi.nlm.nih.gov/38471242/). This tempers the "better than conversation" claim: more disclosure is not shown to mean better prediction.
- Tourangeau, R., & Yan, T. (2007). Sensitive questions in surveys. *Psychological Bulletin, 133*(5), 859–883. https://doi.org/10.1037/0033-2909.133.5.859. Misreporting on sensitive topics is common and situational, and is driven by respondents editing answers "to avoid embarrassing themselves in the presence of an interviewer" **[abstract via OpenAlex]** — [OpenAlex](https://api.openalex.org/works/doi:10.1037/0033-2909.133.5.859)
- Lucas, G. M., Gratch, J., King, A., & Morency, L.-P. (2014). It's only a computer: Virtual humans increase willingness to disclose. *Computers in Human Behavior, 37*, 94–100. https://doi.org/10.1016/j.chb.2014.04.043. Metadata verified; **abstract not seen**; only the title's claim is known — [Crossref](https://doi.org/10.1016/j.chb.2014.04.043)
- LLMs as raters: Levkovich, I., & Elyoseph, Z. (2023). Suicide risk assessments through the eyes of ChatGPT-3.5 versus ChatGPT-4: Vignette study. *JMIR Mental Health, 10*, e51232. https://doi.org/10.2196/51232. On vignettes, GPT-4's estimate of attempt likelihood matched the norms of 379 professionals (mean Z 0.01). **GPT-3.5 markedly underestimated risk (Z −0.83)**, and GPT-4 overestimated psychache **[abstract]** — [PubMed 37728984](https://pubmed.ncbi.nlm.nih.gov/37728984/). These are vignettes, not real users' writing.

### Inferences
- **The size of the signal.** Single word-category markers are weak (r ≈ .10) and non-specific: they mark distress, not suicide. Detection that works relies on whole-text models, and even these reach only AUC 0.62–0.75 when labels come from validated measures on ordinary posts (Ophir et al. 2020). They look strong (AUC ~0.9) mainly under 1:1 matched, retrospective designs (Coppersmith et al. 2018).

- **PPV at realistic base rates.** This is my calculation from Coppersmith et al.'s operating point and is illustrative, not from a source. PPV = sens × p / (sens × p + FPR × (1 − p)), with TPR 0.85 and FPR 0.10:

  | Prevalence p | PPV |
  |---|---|
  | 50% (the study's matched design) | 0.89 |
  | 5% | 0.31 |
  | 1% | 0.079 |
  | 0.5% | 0.041 |

  With TPR 0.70 at p = 1%, PPV ≈ 0.066. Even at the best published operating point, most flags would be false at app-population base rates. Belsher et al. (2019) show the same collapse empirically (PPV ≤ 1% for death).
- **Design consequence for PoesIA.** The safety pause should be tuned as a **high-sensitivity, low-cost check-in** (offer resources, ask the user), not as a risk *prediction*. Any metric in the report should be given as PPV at a stated base rate, not as AUC or accuracy on balanced data.
- **On "better than conversation".** The evidence supports *more disclosure in self-administered or written formats*: 2–4× more ideation on self-report than in clinician interview (Gao et al. 2015), kappa 0.07 (Vera-Varela et al. 2022), and patients preferring the computer interview (Greist et al. 1973). It does **not** show better *prediction*: Nobile et al. (2024) found comparable prediction. "Machine beats clinician" exists only on the genuine-versus-simulated suicide-note task (Pestian et al. 2010) and in a 1973 retrospective study. The report should claim "people may disclose more in writing", not "software detects risk better than clinicians".
- **Poems are a domain shift.** Poetry uses metaphor, persona and dark imagery deliberately, so classifiers trained on Reddit or Twitter can be expected to over-flag (Harrigian et al. 2020 shows cross-platform loss for depression). Handelman & Lester (2007) shows that positive emotion and future tense can appear in notes from people who completed suicide. Both argue against keyword-style screening.
- **Language coverage.** The evidence base is overwhelmingly English. For Spanish there is descriptive work (García-Martínez et al. 2022; García-Caballero et al. 2012) and two clinical disagreement studies from Spain and France. No Italian-language study was found.

### Gaps
- **No prospective study predicting suicidal behaviour from writing** with realistic prevalence was found. CLPsych 2021 and Coppersmith et al. 2018 are retrospective case-control designs with 1:1 matching.
- **No head-to-head prospective comparison of a text classifier against clinician assessment** on the same patients was found. The only clinician comparisons are Pestian et al. 2010 (notes, genuine vs simulated) and Shing et al. 2018 (experts as the *reference standard*, not as competitors).
- Stirman & Pennebaker's full text was not seen (emotion and death-word results, statistics). No replication of the poetry finding in a larger or prospective sample was found; a Semantic Scholar search surfaced only a 2021 Spanish-language clustering paper on poems by suicidal and non-suicidal authors (Revista de Investigación en Tecnologías de la Información, https://doi.org/10.36825/riti.09.18.002), which was not seen.
- Lightman et al. (songwriters' lyrics, CogSci 2007) and Mulholland & Quinn (lyricist classification, IJCNLP 2013) were not found in Crossref and not verified.
- Results of CLPsych 2022 and 2024 (LLM evidence-highlighting) were not read. The exact Coppersmith et al. 2018 AUCs come via MacAvaney et al. 2021, not seen in the figure itself.
- Population base rates for suicidal ideation or attempts (e.g. Nock et al. 2008, Br J Psychiatry, https://doi.org/10.1192/bjp.bp.107.040113) were not verified in this session, so the PPV table uses illustrative prevalences.

---

## Q4. Studies of risk disclosure or detection inside creative-writing or poetry apps and writing platforms

### Takeaway
**None found.** No peer-reviewed study was identified that measures suicide-risk disclosure, or evaluates risk detection, inside a creative-writing, poetry-writing or AI-assisted writing app. The nearest evidence is:
- retrospective analyses of published poems and lyrics by famous artists;
- social-media posts (Reddit, Twitter, Facebook);
- diary-text depression screening with LLMs (not suicide, not creative writing).

PoesIA would be operating in an unstudied setting. The report should say so and treat its own safety-pause logs (with consent) as the first evidence.

### Cited findings
- Poetry and lyrics work is retrospective and biographical: Wiltsey Stirman & Pennebaker 2001 (18 poets) — [PubMed](https://pubmed.ncbi.nlm.nih.gov/11485104/). A thematic analysis of 674 songs referencing suicide (Parrott & Park, *Health Communication*, 2024, https://doi.org/10.1080/10410236.2024.2326698; **metadata from PubMed listing only, not seen**) — [PubMed 38450700](https://pubmed.ncbi.nlm.nih.gov/38450700/). A single-artist lyric analysis (Conway et al., *IJERPH* 2023, https://doi.org/10.3390/ijerph20166621; **not seen**) — [PubMed 37623204](https://pubmed.ncbi.nlm.nih.gov/37623204/)
- Nearest app-based text screening: an LLM depression screen on user diary text (Shin et al., *JMIR* 2024, https://doi.org/10.2196/54617; **title from PubMed listing only, not seen**) — [PubMed 39292502](https://pubmed.ncbi.nlm.nih.gov/39292502/). It is about depression, not suicide, and journaling, not poetry.
- Searches that found nothing on this question:
  - PubMed: `(writing OR journaling OR diary) AND app AND suicid* AND (disclosure OR detection OR language)` (10 hits, none a creative-writing platform);
  - PubMed: `(poem* OR poetry OR lyrics) AND (suicid* OR depress*) AND (language OR linguistic OR "natural language processing" OR classif*)` (59 hits; the top 8 inspected were case studies, reviews of reading, or thematic analyses);
  - Semantic Scholar: "suicidal ideation detection poetry poems" and "depression detection poems natural language processing" (no relevant detection study);
  - web search: "suicide risk disclosure creative writing platform poetry posts detection study" (only social-media studies returned) — [WebSearch result: Ophir et al.](https://www.nature.com/articles/s41598-020-73917-0); [García-Martínez et al.](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9157318/)

### Inferences
- Every performance figure in Q3 comes from a different text genre, platform, motive and language mix than PoesIA's. Expect a domain shift, most likely toward **more false positives**, because poetry licenses dark imagery and persona voice.
- The ethically safer framing is **disclosure-supporting, not surveillance**. The app offers a pause and resources when the writing contains explicit risk language, tells users this up front, and does not claim to predict.

### Gaps
- No study of creative-writing platforms (Wattpad, AllPoetry, r/OCPoetry and similar) and suicide-risk content was found, though a fuller search of ACL Anthology, arXiv and IberLEF (e.g. Spanish MentalRiskES) could still turn something up. This session did not run those searches.
- No study measures whether users of AI writing assistants disclose more or less than they would to a person.

### Source register (all questions)
DOI verified on Crossref unless noted; "seen" = what was read.

| Source | DOI / URL | Seen |
|---|---|---|
| Pennebaker & Beall 1986 | 10.1037/0021-843X.95.3.274 | metadata only (abstract and full text **not seen**) |
| Smyth 1998 | 10.1037/0022-006X.66.1.174 | abstract |
| Frattaroli 2006 | 10.1037/0033-2909.132.6.823 | abstract |
| Reinhold, Bürkner & Holling 2018 | 10.1111/cpsp.12224 | abstract (pooled g not seen) |
| Pavlacic et al. 2019 | 10.1177/1089268019831645 | abstract |
| Gerger et al. 2022 | 10.1017/S0033291721000143 | abstract |
| Kovac & Range 2002 | 10.1521/suli.32.4.428.22335 | abstract |
| Vukčević Marković et al. 2020 | 10.3389/fpsyg.2020.587282 | abstract |
| Gortner, Rude & Pennebaker 2006 | 10.1016/j.beth.2006.01.004 | abstract |
| Baikie & Wilhelm 2005 | 10.1192/apt.11.5.338 | abstract |
| Kassab, Jayatunge & Bou Khalil 2026 | 10.1016/j.psychres.2025.116897 | abstract |
| Porras-Segovia et al. 2024 | 10.1007/s11920-024-01511-6 | abstract |
| Mundy et al. 2022 | 10.18261/njach.4.1.1 | abstract |
| Heimes 2011 | 10.1016/j.aip.2010.09.006 | metadata only (**not seen**) |
| Kaufman 2001 | 10.1002/j.2162-6057.2001.tb01220.x | abstract |
| Wiltsey Stirman & Pennebaker 2001 | 10.1097/00006842-200107000-00001 | abstract (full text not seen) |
| Tackman et al. 2019 | 10.1037/pspp0000187 | abstract |
| Edwards & Holtzman 2017 | 10.1016/j.jrp.2017.02.005 | metadata only (**not seen**) |
| Rude, Gortner & Pennebaker 2004 | 10.1080/02699930441000030 | abstract |
| Pestian et al. 2010 | 10.4137/BII.S4706 | abstract |
| Pestian et al. 2012 | 10.4137/BII.S9042 | abstract |
| Pestian et al. 2017 | 10.1111/sltb.12312 | abstract |
| Handelman & Lester 2007 | 10.1027/0227-5910.28.2.102 | abstract |
| García-Caballero et al. 2012 | 10.1016/S0924-9338(12)75586-4 | conference abstract |
| Coppersmith et al. 2018 | 10.1177/1178222618792860 | full text (Europe PMC) |
| Ophir et al. 2020 | 10.1038/s41598-020-73917-0 | abstract |
| García-Martínez et al. 2022 | 10.2196/31800 | abstract |
| Shing et al. 2018 | 10.18653/v1/W18-0603 | full text (ACL Anthology) |
| Zirikly et al. 2019 | 10.18653/v1/W19-3003 | full text (ACL Anthology) |
| MacAvaney et al. 2021 | 10.18653/v1/2021.clpsych-1.7 | full text (ACL Anthology) |
| Tsakalidis et al. 2022 | 10.18653/v1/2022.clpsych-1.16 | metadata only (**not seen**) |
| Chim et al. 2024 | 10.18653/v1/2024.clpsych-1.15 | metadata only (**not seen**) |
| Harrigian, Aguirre & Dredze 2020 | 10.18653/v1/2020.findings-emnlp.337 | abstract |
| Chancellor & De Choudhury 2020 | 10.1038/s41746-020-0233-7 | abstract |
| Bernert et al. 2020 | 10.3390/ijerph17165929 | abstract |
| Belsher et al. 2019 | 10.1001/jamapsychiatry.2019.0174 | abstract |
| Franklin et al. 2017 | 10.1037/bul0000084 | abstract |
| Greist et al. 1973 | 10.1176/ajp.130.12.1327 | abstract |
| Vera-Varela et al. 2022 | 10.1080/13811118.2021.1945984 | abstract |
| Gao et al. 2015 | 10.1016/j.jpsychires.2014.09.011 | abstract |
| Nobile et al. 2024 | 10.1016/j.psychres.2024.115833 | abstract |
| Tourangeau & Yan 2007 | 10.1037/0033-2909.133.5.859 | abstract |
| Lucas et al. 2014 | 10.1016/j.chb.2014.04.043 | metadata only (**not seen**) |
| Levkovich & Elyoseph 2023 | 10.2196/51232 | abstract |
