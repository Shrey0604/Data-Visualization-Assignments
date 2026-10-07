- Raw merge: 49266 rows x 20 cols from 50 subreddit files.
- Duplicate post ids: 0.
- Timestamps: 48279 ISO + 987 M/D/YYYY H:MM parsed; range 2011-09-27 04:17:32 .. 2024-09-11 07:13:13 UTC.
- Dropped columns: num_awards (all 49266 zero), crosspost_subreddits (99.35% missing), is_bot (8.53% missing), is_megathread (21 True), body (82.79% missing).
- Domains: 3420 raw -> 3082 after prefix stripping, alias merging and reduction to the registrable domain (eTLD+1).
- Rows kept: 49266 (no rows dropped; the corpus is the top tail by construction, so extremes are kept).
- Posts per year: {2011: 1, 2012: 2, 2013: 5, 2014: 168, 2015: 602, 2016: 1747, 2017: 6266, 2018: 8096, 2019: 8465, 2020: 11493, 2021: 6279, 2022: 3930, 2023: 1589, 2024: 623}
- Topic categories: {'Q&A and advice': 8, 'Text humour and stories': 4, 'News, science and tech': 8, 'Memes and GIFs': 4, 'Photos and curiosities': 7, 'Creative and lifestyle': 5, 'Entertainment and media': 10, 'Knowledge and curiosity': 4}
- domain_class counts: {'reddit-hosted media': 15079, 'self post': 13135, 'external website': 13010, 'imgur': 4112, 'youtube': 3040, 'other video host': 890}
- Network: posts linking to external domains = 21052 of 49266; distinct external domains = 3035; kept domains with >= 3 posts = 628.
  Nodes = 671 (43 subreddits + 628 domains); edges = 2350; total edge weight = 18245 posts.
  Subreddits with no qualifying external link (absent from graph): ['AskReddit', 'LifeProTips', 'NoStupidQuestions', 'Showerthoughts', 'explainlikeimfive', 'personalfinance', 'relationship_advice']
- Treemap hierarchy h1_topic: category -> subreddit -> post_type; leaves = 135.
- Treemap hierarchy h2_media: post_type -> domain_class -> category -> subreddit; leaves = 250.
- Treemap hierarchy h3_time: era -> year -> category -> subreddit; leaves = 486.
- Parallel coordinates: stratified sample 40/subreddit (seed 42) = 2000 posts; axes = ['dec_year', 'hour_utc', 'title_len', 'upvote_ratio', 'score', 'num_comments', 'num_crossposts']; log10 transform for score, log10(x+1) for comments and crossposts.
  k-means silhouette by k: {3: 0.241, 4: 0.248, 5: 0.229, 6: 0.221, 7: 0.226, 8: 0.194} -> k = 4.
  cluster sizes: [552, 675, 553, 220]
- Time series window 2016-01..2024-08 (104 months, 48442 posts = 98.3% of corpus); months with zero posts in a category are true zeros.
