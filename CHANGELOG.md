# Changelog

## [0.8.2](https://github.com/hberg539/memebase/compare/v0.8.1...v0.8.2) (2026-03-04)


### Bug Fixes

* **upload:** update leftover uuid references to id ([3823c21](https://github.com/hberg539/memebase/commit/3823c211c61e91370eec9228f1097e51ccd39f3a))

## [0.8.1](https://github.com/hberg539/memebase/compare/v0.8.0...v0.8.1) (2026-03-04)


### Refactoring

* centralize rename and delete operations into service.py ([0183776](https://github.com/hberg539/memebase/commit/0183776973078127222ea325e9b66a73172203aa))
* **db:** rename uuid to id/meme_id across codebase ([9e9a550](https://github.com/hberg539/memebase/commit/9e9a5503f2a30401414595594f6b3a66d31f1edb))

## [0.8.0](https://github.com/hberg539/memebase/compare/v0.7.0...v0.8.0) (2026-02-26)


### Features

* add URL scraping via gallery-dl for webpage links ([8a2c9f1](https://github.com/hberg539/memebase/commit/8a2c9f147143dab0ae9fc80505c5f6f8b7482e6c))
* limit gallery-dl downloads via DownloadJob subclass with global counter ([463d43f](https://github.com/hberg539/memebase/commit/463d43f514ff20241d3920c8600c09753524abf6))


### Refactoring

* extract temp directory management into dedicated module ([6665a6e](https://github.com/hberg539/memebase/commit/6665a6e612d81fc236df292fd263432f0ebb951f))
* move max_files from hardcoded constant to config ([b1648fb](https://github.com/hberg539/memebase/commit/b1648fb995332b8f24b6947a109d73800bfc5d1a))
* use gallery-dl for all URLs with custom catch-all extractor ([ed5464d](https://github.com/hberg539/memebase/commit/ed5464dbc8541da0cc05a4ebccd714f3e8bf1e7a))


### Documentation

* consolidate URL scraping into upload feature bullet ([f4ae476](https://github.com/hberg539/memebase/commit/f4ae47601e4ab723dc4ed99777cbc8fcd0810604))
* rewrite AI disclaimer ([21dfcf3](https://github.com/hberg539/memebase/commit/21dfcf3a78c974f95c01953bcc256de5dc737b31))


### CI/CD

* add GitHub Actions lint workflow ([706ae76](https://github.com/hberg539/memebase/commit/706ae7618a9608b83a61e213fa0a989653dac5e9))
* run lint on all branches ([43c2ef4](https://github.com/hberg539/memebase/commit/43c2ef49a1373e172d2085aaa59b3353824c629f))

## [0.7.0](https://github.com/hberg539/memebase/compare/v0.6.0...v0.7.0) (2026-02-24)


### Features

* **db:** add lightweight SQLite migration system ([d54017e](https://github.com/hberg539/memebase/commit/d54017e7f3afe707b92c8b134db9f130c5999816))


### Refactoring

* add parse_ext helper to centralize extension extraction ([443c5de](https://github.com/hberg539/memebase/commit/443c5de8371d7a5c67af3391f433a57e01a8d173))
* convert to Flask app factory pattern ([c49f9f3](https://github.com/hberg539/memebase/commit/c49f9f398f0b75101b9f76e7f74dae25e54a8a4e))
* extract logging setup into dedicated module ([9fbd7a0](https://github.com/hberg539/memebase/commit/9fbd7a03874699bd59cd515245e8ec0560276fb7))
* rename load_config to get_config ([bfa5649](https://github.com/hberg539/memebase/commit/bfa5649266bb95d24cab0dd3ab21005cc32a5c1c))

## [0.6.0](https://github.com/hberg539/memebase/compare/v0.5.2...v0.6.0) (2026-02-24)


### Features

* add clipboard paste upload ([7aba520](https://github.com/hberg539/memebase/commit/7aba520fcd84f9b10f296d5509a3ffc32240ae3b))
* **thumbnails:** enable thumbnails by default ([43eacc7](https://github.com/hberg539/memebase/commit/43eacc7cce550b8e70916f41426bb94c78d30340))
* **ui:** add configurable ui.title setting ([f030143](https://github.com/hberg539/memebase/commit/f030143b44c3ec0ba8f99b33837228f91a9d9c2f))
* **ui:** add theming system, built-in themes, and custom theme support ([e0e8b4b](https://github.com/hberg539/memebase/commit/e0e8b4ba5fb0c7d841bb9fc4e17a3f578d6b9dbd))


### Refactoring

* **ui:** make pagination sliding window configurable and simplify logic ([742a0e7](https://github.com/hberg539/memebase/commit/742a0e76fed9f8501bcd3f51c29f3f89f91c0b90))
* **ui:** rename ambiguous CSS class names for theming clarity ([e969670](https://github.com/hberg539/memebase/commit/e9696707fe959d2d0dbbc335e1ca9602c4d1f442))


### Documentation

* add model step to AI setup instructions ([c2bc9bd](https://github.com/hberg539/memebase/commit/c2bc9bdd54be54d238b7eac03cfa8eed45854bcc))
* add prompt customization note to AI section ([3001f56](https://github.com/hberg539/memebase/commit/3001f56c587de9dd410b006cf41a95deb2eb0fff))
* add section links to configuration table ([2a642e5](https://github.com/hberg539/memebase/commit/2a642e57d91eaf77ea28f218831e82cd6a818de8))
* add sub-headers to TOC ([0b400c0](https://github.com/hberg539/memebase/commit/0b400c026d9a6558885c9ef099bb4561ca03ffd0))
* add table of contents and rename data storage section ([12a299a](https://github.com/hberg539/memebase/commit/12a299a9dbbd2d72d515cde3ce04527627afc749))
* add themes to features list ([49016fe](https://github.com/hberg539/memebase/commit/49016fe92f6833d6d29056103221ea2985310117))
* move hotkeys section up and update escape description ([de43103](https://github.com/hberg539/memebase/commit/de4310334b5112b90f599f94139776a40d91c982))
* rename README sections ([97d4975](https://github.com/hberg539/memebase/commit/97d4975081044add37b2895bb05287bb8cf80ed3))
* update python badge to 3.11+ ([0c3af15](https://github.com/hberg539/memebase/commit/0c3af15f4502d303b86fd63a962d18111710f7ef))

## [0.5.2](https://github.com/hberg539/memebase/compare/v0.5.1...v0.5.2) (2026-02-23)


### Bug Fixes

* **ui:** show filename in bulk auto-detect failure alerts ([98ee784](https://github.com/hberg539/memebase/commit/98ee78486728d63746bd4977bb8deafa864819a2))


### Documentation

* add AI auto-detect usage info to README ([b7a96d9](https://github.com/hberg539/memebase/commit/b7a96d9243ecd8baf63271d832004baca408f145))

## [0.5.1](https://github.com/hberg539/memebase/compare/v0.5.0...v0.5.1) (2026-02-23)


### Bug Fixes

* **ui:** per-item toasts and correct progress counter for bulk auto-detect ([75f91e3](https://github.com/hberg539/memebase/commit/75f91e33c735f58c5ff8a9317c63b588c6505b30))


### Documentation

* update main screenshot ([f9fc31d](https://github.com/hberg539/memebase/commit/f9fc31d27c9832bc24b254249efa38fcfbbfdb75))

## [0.5.0](https://github.com/hberg539/memebase/compare/v0.4.1...v0.5.0) (2026-02-23)


### Features

* add on-demand thumbnail generation for grid view ([24034f2](https://github.com/hberg539/memebase/commit/24034f2d6aa19636638496a01502e15707504d00))
* **db:** add ext column to memes table for cleaner extension queries ([38154ff](https://github.com/hberg539/memebase/commit/38154ff08da387d24c06a5b2aae39c6a342c600c))
* make server host/port configurable via config.toml ([f532f86](https://github.com/hberg539/memebase/commit/f532f86284cf17b628016b336d6a204cabaece20))
* return generated 404 placeholder image for missing memes/thumbnails ([91ea28e](https://github.com/hberg539/memebase/commit/91ea28e8551c34f7651bf7ee3b7063de399e7e92))
* **ui:** add masonry layout option via grid.layout config ([5f733ac](https://github.com/hberg539/memebase/commit/5f733ac439e35b72f10e043b162e7dcfddb3ac7d))
* **ui:** auto-calculate per_page from viewport size ([47287fc](https://github.com/hberg539/memebase/commit/47287fcff358b6471b9d6cfedbbb55064f186ea0))
* **ui:** enable clear button only when filters or search are active ([929d7f7](https://github.com/hberg539/memebase/commit/929d7f7edb0d868d2205cd34ebe6edf766d3de7f))
* **ui:** show title and tags only on card hover, bump default thumbnail size to 220 ([0462509](https://github.com/hberg539/memebase/commit/0462509e76d07f3ebd60349975d6b170cf820ac4))
* **ui:** show warning toast for unsupported file types on upload ([15f6a6c](https://github.com/hberg539/memebase/commit/15f6a6c621215b9b0546026df255670f1e19431a))


### Bug Fixes

* scale thumbnails by short side to prevent pixelation on tall images ([28ce073](https://github.com/hberg539/memebase/commit/28ce073cc369f737e5b5faa05eee98b8112fc49a))
* **ui:** await page load before scrolling to top on pagination ([65b932a](https://github.com/hberg539/memebase/commit/65b932a87f5ea06cdd8f4a1639eeb7ff82643761))
* **ui:** scroll to top before loading on pagination ([75dc534](https://github.com/hberg539/memebase/commit/75dc534fea97ae45999b838e5e2d703210168afe))
* **ui:** scroll to top before loading on pagination ([2e9d74a](https://github.com/hberg539/memebase/commit/2e9d74a8469bbb26bfad96451017d20ad1d59a9a))
* **ui:** show active process count instead of completed in bulk auto-detect ([758447f](https://github.com/hberg539/memebase/commit/758447fac8091e22d2b5173da331abcb540debdc))


### Refactoring

* remove copy_count feature ([2b812e9](https://github.com/hberg539/memebase/commit/2b812e948c973a6ce505737d6ccda19bd651642a))

## [0.4.1](https://github.com/hberg539/memebase/compare/v0.4.0...v0.4.1) (2026-02-23)


### Bug Fixes

* **ui:** keep drop zone highlighted when dragging over child elements ([fa8d49b](https://github.com/hberg539/memebase/commit/fa8d49b9b78e0382f5fa5e73d9892a725aeab159))


### Refactoring

* extract shared dialog utilities into dialog.js ([4d7ef74](https://github.com/hberg539/memebase/commit/4d7ef74e0aa56853340d105fb663354042233a6d))
* normalize log strings to key=value format with timestamps ([0454562](https://github.com/hberg539/memebase/commit/0454562691317678719890c373f7c271ac9af558))


### Miscellaneous

* auto-restart container unless explicitly stopped ([02064b7](https://github.com/hberg539/memebase/commit/02064b75b6ec649a6758be5f399ae3f94a5ac33c))
* drop style commit type from changelog and pre-commit hook ([f2d0e90](https://github.com/hberg539/memebase/commit/f2d0e90877535363f9cc0e4d5c4cb6da96d9d81c))

## [0.4.0](https://github.com/hberg539/memebase/compare/v0.3.0...v0.4.0) (2026-02-23)


### Features

* trigger search immediately on Enter key press ([2555278](https://github.com/hberg539/memebase/commit/2555278c38e8b78f4d432d6604888888c007f743))


### Bug Fixes

* **frontend:** cross-browser compatibility for Safari and Chrome ([02dc0d4](https://github.com/hberg539/memebase/commit/02dc0d482da754c1608ff23db0b4fff465e1c582))
* keep duplicate files on disk during meme registration ([95f576c](https://github.com/hberg539/memebase/commit/95f576caf3544b67d91e51960f6dd3077499616a))
* **service:** skip rename and DB update when AI-suggested name is unchanged ([b60a31a](https://github.com/hberg539/memebase/commit/b60a31a867525087d3616c3e52fb7b09ea2b877c))
* **ui:** keyboard handling for bulk tag and auto-detect modals ([6f1567e](https://github.com/hberg539/memebase/commit/6f1567e9636956a2ed7373a8295764fbcee462c6))
* use Flask g object for per-request DB connection management ([2df5fcc](https://github.com/hberg539/memebase/commit/2df5fcc5bbafd6b6f06c85896b8410e831716f88))


### Refactoring

* **ai:** accept model and prompt as parameters in analyze_meme ([aa6fb3e](https://github.com/hberg539/memebase/commit/aa6fb3ea4d3c117f3462c6dbeb855d65f18aac5f))
* **app:** extract business logic from route handlers into service layer ([0424337](https://github.com/hberg539/memebase/commit/04243371883a461056b2167b5ac7ffc494e5586d))
* **app:** move late imports to module level ([3ac2034](https://github.com/hberg539/memebase/commit/3ac203479cfcbfc19a19dc25a307a60d3c69ed1b))
* centralize config loading into dedicated config module ([8428e77](https://github.com/hberg539/memebase/commit/8428e77887192e579a48efb2cecc179deca1a428))
* **db:** decompose query_memes into helper functions ([9e84087](https://github.com/hberg539/memebase/commit/9e840873bac7c3510d3349e087ebede6e532b5d4))
* **db:** move normalize_tags from db.py to util.py ([5fc3499](https://github.com/hberg539/memebase/commit/5fc34993c73948af2b87089d3c8ac7a09bd58a06))
* migrate from os.path to pathlib.Path for all filesystem operations ([5f33712](https://github.com/hberg539/memebase/commit/5f3371206eba73d9a17edeb3fb114c123190c64e))
* turn src/ into proper memebase package ([338a546](https://github.com/hberg539/memebase/commit/338a546fcac4aeb884098baf62d44e8840107fb4))
* **types:** add AppConfig TypedDict for structured config access ([6d37462](https://github.com/hberg539/memebase/commit/6d37462fe1d05f60dddad6627dec040f6cb36a8c))
* **types:** add Meme TypedDict for structured meme records ([3767155](https://github.com/hberg539/memebase/commit/3767155001f55ca64ca8e0192106d07e18fb0007))
* **types:** replace magic error strings with MemeError StrEnum ([ce1a5a0](https://github.com/hberg539/memebase/commit/ce1a5a0c897a1bb70756f41a3688355e773e3779))


### Performance

* cache config in memory after first load ([7f7d588](https://github.com/hberg539/memebase/commit/7f7d588da80d2c7c3ee387c0ce4569d8c714afde))
* **db:** add indexes, fix N+1 query, and batch tag operations ([2108d72](https://github.com/hberg539/memebase/commit/2108d72b6696f0ad5a904f7701f2f0cf3cf85091))
* **db:** use RETURNING clause in increment_copy_count and delete_meme_row ([2ddd781](https://github.com/hberg539/memebase/commit/2ddd78140f249df9904d18250df28fca838f13aa))


### Styling

* extract CACHE_MAX_AGE constant, consolidate TOML parsing, simplify normalize_tags ([c12d84e](https://github.com/hberg539/memebase/commit/c12d84e7ce8ac2b461e6e2b3f487bdca5718e6cf))


### Tests

* **api:** add HTTP-level endpoint tests with mocked service/DB ([7f4a20f](https://github.com/hberg539/memebase/commit/7f4a20ff8d35647e47b5304b1095014a6cb4d7a5))
* **api:** add URL scheme validation tests for meme download endpoint ([15deb23](https://github.com/hberg539/memebase/commit/15deb23f95f781cdb29b05ec00dee3903a011bc6))
* **config:** add deep-merge tests for old/partial/empty configs ([49762f5](https://github.com/hberg539/memebase/commit/49762f575f03f072de19298f66502f20d3964177))


### Build System

* **config:** bump minimum Python version to 3.11 ([ebae0b7](https://github.com/hberg539/memebase/commit/ebae0b79a38e4f47ccb914384365b775ae70dbc2))
* disable debug mode in Docker image ([f52f9e7](https://github.com/hberg539/memebase/commit/f52f9e7d4b294a0b40665d1315e7d85a9adeb046))


### Miscellaneous

* ignore .claude/ directory ([85ad159](https://github.com/hberg539/memebase/commit/85ad1594be65b2b745f892988846bdf127e9551f))
* **lint:** enable stricter ruff rules and fix all violations ([21df54b](https://github.com/hberg539/memebase/commit/21df54b5ae9db4a2338fb9feb432cec9ed35db3e))

## [0.3.0](https://github.com/hberg539/memebase/compare/v0.2.0...v0.3.0) (2026-02-23)


### Features

* **ui:** add rainbow gradient favicon with build script ([949b34b](https://github.com/hberg539/memebase/commit/949b34b547c68785372c60ad712fbf8cffc57411))


### Bug Fixes

* **config:** use local build instead of remote image in docker-compose ([28ca6e9](https://github.com/hberg539/memebase/commit/28ca6e9a9a5bbff46342540c2b726ff285e8dc59))
* **grid:** truncate long meme filenames with ellipsis while preserving extension ([bd268f0](https://github.com/hberg539/memebase/commit/bd268f0e8afb97767137e4cce40ac1e14c323359))
* **security:** validate URL scheme in upload-from-url endpoint ([299987c](https://github.com/hberg539/memebase/commit/299987c9d1ecd7caac44c2d2f0bbd348dbe53b5e))


### Refactoring

* extract service layer, split ai.py, deduplicate upload logic ([b4f1720](https://github.com/hberg539/memebase/commit/b4f17200899e7727258091689f62c2f890f1419f))


### Documentation

* add links to README badges ([5d42b0c](https://github.com/hberg539/memebase/commit/5d42b0ca116ff2f7734bac4e3aec29b423077dcb))
* add test status badge to README ([67f8a07](https://github.com/hberg539/memebase/commit/67f8a07100512fc693f6ab35622d0eee0473ab7a))
* update AGENTS.md with service layer, new tests, and CI info ([51ceaa6](https://github.com/hberg539/memebase/commit/51ceaa6d75c2d9b629dc31ed5f470a86e8f6d440))


### Styling

* add type hints to all Python source functions ([cade51a](https://github.com/hberg539/memebase/commit/cade51ac2feb6b057095ca48f514645e761909c1))


### Build System

* sync uv.lock version via release-please extra-files ([08685f6](https://github.com/hberg539/memebase/commit/08685f6593a7704887becc9fc0130d85afd4ecbb))


### CI/CD

* add pytest workflow for every push and PR ([5b6b6c0](https://github.com/hberg539/memebase/commit/5b6b6c0918cf271f56d8a4a666c15bed92b75b33))
* test on Python 3.10 and 3.14 ([2e69b9a](https://github.com/hberg539/memebase/commit/2e69b9af207bfeb937dc01d32d04b86b8c8ce538))


### Miscellaneous

* remove TODOS.md ([c3ac1ec](https://github.com/hberg539/memebase/commit/c3ac1ece3543f0910f0dd57c58f7fdb9a068ecd0))

## [0.2.0](https://github.com/hberg539/memebase/compare/v0.1.0...v0.2.0) (2026-02-23)


### Features

* initial memebase implementation ([e086855](https://github.com/hberg539/memebase/commit/e0868552346dbd21f1b7da95e0c709ba75568dfe))
