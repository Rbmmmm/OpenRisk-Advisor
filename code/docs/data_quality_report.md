# OpenDigger 数据质量报告

生成时间：2026-01-13T16:01:53Z

数据源配置：`configs/sources.yaml`

指标配置：`configs/metrics.yaml`

SQLite：`data/sqlite/opendigger.db`

## 覆盖情况

| repo 数 | metric 数 | repo×metric 组合数 |
| --- | --- | --- |
| 196 | 31 | 6076 |

## 抓取情况（按状态分组）

| 状态 | 数量 |
| --- | --- |
| http_404 | 979 |
| ok | 5097 |

## 解析情况

| parsed_ok | raw_only | parse_error |
| --- | --- | --- |
| 5069 | 0 | 1007 |

## 每个仓库抓取健康度

| repo | ok | 404 | network_fail | ok_rate | 404_rate | network_fail_rate |
| --- | --- | --- | --- | --- | --- | --- |
| 33-ohoh/33-ohoh | 28 | 3 | 0 | 90.32% | 9.68% | 0.00% |
| 7Sence/Rise-Beta | 12 | 19 | 0 | 38.71% | 61.29% | 0.00% |
| ACINQ/phoenixd | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| AG-597/Csolver | 12 | 19 | 0 | 38.71% | 61.29% | 0.00% |
| Actindo-AG/Documentation | 25 | 6 | 0 | 80.65% | 19.35% | 0.00% |
| Ada-C11/hash-practice | 16 | 15 | 0 | 51.61% | 48.39% | 0.00% |
| AgoraIO/Basic-Video-Call | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| Alla-java/ADS-online | 26 | 5 | 0 | 83.87% | 16.13% | 0.00% |
| CSE2024-SDP-Team5/thu-space-invaders | 24 | 7 | 0 | 77.42% | 22.58% | 0.00% |
| CSolverV2/hCaptcha-ID-Decoder | 13 | 18 | 0 | 41.94% | 58.06% | 0.00% |
| CarlosMontano2005/BEST_PLAYER_2024 | 22 | 9 | 0 | 70.97% | 29.03% | 0.00% |
| Cerebellum-Network/grant-program | 25 | 6 | 0 | 80.65% | 19.35% | 0.00% |
| ClickHouse/ClickHouse | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| CypherV2/Donarev-API | 13 | 18 | 0 | 41.94% | 58.06% | 0.00% |
| DP2-c2-028/Acme-SF-D04 | 10 | 21 | 0 | 32.26% | 67.74% | 0.00% |
| DXVVAY/hcaptcha-reverse | 13 | 18 | 0 | 41.94% | 58.06% | 0.00% |
| DankIdeaCentral/migrate-app | 27 | 4 | 0 | 87.10% | 12.90% | 0.00% |
| DataBiosphere/data-explorer-indexers | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| DataDog/swift-dogstatsd | 28 | 3 | 0 | 90.32% | 9.68% | 0.00% |
| DeepakReddyG/ZeroOneCodeClub_FirstWebDevProject | 29 | 2 | 0 | 93.55% | 6.45% | 0.00% |
| Desarrollo-PI/Proyecto-Videojuego-SB | 23 | 8 | 0 | 74.19% | 25.81% | 0.00% |
| DorinGI/event_booster_team_4 | 23 | 8 | 0 | 74.19% | 25.81% | 0.00% |
| Dwit-Tech/core-banking-service | 22 | 9 | 0 | 70.97% | 29.03% | 0.00% |
| EngineerFocus/FocusPro | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| Eugeshakw/water-tracker | 23 | 8 | 0 | 74.19% | 25.81% | 0.00% |
| Expensify/App | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| FirelyTeam/firely-docs-firely-server | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| GDG-ADGIPS/Hack-Chill-2.0 | 24 | 7 | 0 | 77.42% | 22.58% | 0.00% |
| GoogleCloudPlatform/gke-poc-toolkit | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| GreenUniversityComputerClub/gucc | 25 | 6 | 0 | 80.65% | 19.35% | 0.00% |
| Hexa-Coders-aug23/product_catalog | 24 | 7 | 0 | 77.42% | 22.58% | 0.00% |
| IU3Labs/ToP_2025 | 24 | 7 | 0 | 77.42% | 22.58% | 0.00% |
| IntelAISociety/Hello-world | 17 | 14 | 0 | 54.84% | 45.16% | 0.00% |
| Ionaru/easy-markdown-editor | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| JamesCJ60/Universal-x86-Tuning-Utility | 29 | 2 | 0 | 93.55% | 6.45% | 0.00% |
| JonYoung-dev/andromeda-agile-site | 21 | 10 | 0 | 67.74% | 32.26% | 0.00% |
| JoseChaconUrias/GroceryStore | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| JustTemmie/steam-presence | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| KW-GIRIGIRI/kw-rental-backend | 27 | 4 | 0 | 87.10% | 12.90% | 0.00% |
| KryoEM/relion2 | 28 | 3 | 0 | 90.32% | 9.68% | 0.00% |
| LayerZero-Labs/sybil-report | 23 | 8 | 0 | 74.19% | 25.81% | 0.00% |
| MasseyHackers/mh-githubs | 24 | 7 | 0 | 77.42% | 22.58% | 0.00% |
| Mentoring-Bordeaux/AutonomousCars | 29 | 2 | 0 | 93.55% | 6.45% | 0.00% |
| MetaMask/types | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| Mole1803/SPoRT | 24 | 7 | 0 | 77.42% | 22.58% | 0.00% |
| MyResonance/tickets | 13 | 18 | 0 | 41.94% | 58.06% | 0.00% |
| NVIDIA/TensorRT-LLM | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| Neautrino/python-questions | 29 | 2 | 0 | 93.55% | 6.45% | 0.00% |
| NixOS/nixpkgs | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| Pennebaker/craft-architect | 29 | 2 | 0 | 93.55% | 6.45% | 0.00% |
| QUACK-INTEC/memo-app | 22 | 9 | 0 | 70.97% | 29.03% | 0.00% |
| SWIFTSIM/pipeline-configs | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| Seol-Munhyeok/coby | 29 | 2 | 0 | 93.55% | 6.45% | 0.00% |
| Shuriken-Group/Shuriken-Analyzer | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| StatisticsGreenland/pxmake | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| TeCOS-NIT-Trichy/first-issue-demo | 29 | 2 | 0 | 93.55% | 6.45% | 0.00% |
| Topshelf/Topshelf | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| UMC-WEGO/WEGO_FE_React | 29 | 2 | 0 | 93.55% | 6.45% | 0.00% |
| UnBArqDsw2024-2/2024.2_G10_Recomendacao_Entrega_01 | 28 | 3 | 0 | 90.32% | 9.68% | 0.00% |
| WSU-4110/Able | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| WebKit/WebKit | 25 | 6 | 0 | 80.65% | 19.35% | 0.00% |
| X-lab2017/open-digger | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| XX-net/XX-Net | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| ZimbraOS/zm-docker | 24 | 7 | 0 | 77.42% | 22.58% | 0.00% |
| al-fajri/pre-course | 23 | 8 | 0 | 74.19% | 25.81% | 0.00% |
| alipay/quic-lb | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| anitabaron/cinemania-goit | 25 | 6 | 0 | 80.65% | 19.35% | 0.00% |
| annsh4/module2ASD | 23 | 8 | 0 | 74.19% | 25.81% | 0.00% |
| anthropics/claude-code | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| apache/iotdb | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| archesproject/arches-querysets | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| aternosorg/modbot | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| atomiks/tippyjs-react | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| aws-cloudformation/iac-model-evaluation | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| awslabs/yesiscan | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| babelfish-for-postgresql/postgresql_modified_for_babelfish | 25 | 6 | 0 | 80.65% | 19.35% | 0.00% |
| bmax121/KernelPatch | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| brave/googleads-referral | 13 | 18 | 0 | 41.94% | 58.06% | 0.00% |
| carrot/roots-contentful | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| castorm/kafka-connect-http | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| chatbot-devplus/employee-project-tracker | 21 | 10 | 0 | 67.74% | 32.26% | 0.00% |
| choojs/choo | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| cloudflare/webcm-docs | 29 | 2 | 0 | 93.55% | 6.45% | 0.00% |
| coding-blocks/hackerblocks.projectx | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| conda-forge/aenum-feedstock | 28 | 3 | 0 | 90.32% | 9.68% | 0.00% |
| conda-forge/forte2-feedstock | 23 | 8 | 0 | 74.19% | 25.81% | 0.00% |
| conda-forge/tensorflow-feedstock | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| conda-forge/webtest-feedstock | 23 | 8 | 0 | 74.19% | 25.81% | 0.00% |
| coroo/nova-chartjs | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| cta-observatory/magic-cta-pipe | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| dart-lang/observe | 27 | 4 | 0 | 87.10% | 12.90% | 0.00% |
| dataease/DataEase | 0 | 31 | 0 | 0.00% | 100.00% | 0.00% |
| davidvida/js-reactjs-course | 15 | 16 | 0 | 48.39% | 51.61% | 0.00% |
| department-of-veterans-affairs/va.gov-team | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| digicatapult/morello-ui | 22 | 9 | 0 | 70.97% | 29.03% | 0.00% |
| dinamio/hillel-javaee | 25 | 6 | 0 | 80.65% | 19.35% | 0.00% |
| droibit/flutter_custom_tabs | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| dropout1337/wasm-commenter | 13 | 18 | 0 | 41.94% | 58.06% | 0.00% |
| easy-graph/Easy-Graph | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| elastic/elasticsearch | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| elastic/kibana | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| elixir-lang/highlight.js | 21 | 10 | 0 | 67.74% | 32.26% | 0.00% |
| emrovsky/hcaptcha-blob-encryption | 13 | 18 | 0 | 41.94% | 58.06% | 0.00% |
| emrovsky/x-ms-reference-id | 12 | 19 | 0 | 38.71% | 61.29% | 0.00% |
| encisosystems/set-web | 29 | 2 | 0 | 93.55% | 6.45% | 0.00% |
| eslint/eslintrc | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| facebookresearch/blt | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| falcosecurity/cncf-green-review-testing | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| gamerson/liferay-intellij-plugin | 25 | 6 | 0 | 80.65% | 19.35% | 0.00% |
| getsentry/sentry | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| ghscr/ghscription | 29 | 2 | 0 | 93.55% | 6.45% | 0.00% |
| gnosis/dx-services | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| godotengine/godot | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| google-gemini/gemini-cli | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| grafana/grafana | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| grafana/otel-operator-demo | 23 | 8 | 0 | 74.19% | 25.81% | 0.00% |
| gudaoxuri/dew | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| hackclub/assemble-preflight-web | 29 | 2 | 0 | 93.55% | 6.45% | 0.00% |
| harness/harness-core | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| hashicorp/terraform-foundational-policies-library | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| heyitsmdr/armeria | 29 | 2 | 0 | 93.55% | 6.45% | 0.00% |
| hol16046/wdd430_group | 28 | 3 | 0 | 90.32% | 9.68% | 0.00% |
| home-assistant/core | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| hpi-swa-teaching/SWT18-Project-04 | 13 | 18 | 0 | 41.94% | 58.06% | 0.00% |
| iaurg/rocketseatdevs | 24 | 7 | 0 | 77.42% | 22.58% | 0.00% |
| illyasviel/crowds | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| jenkinsci/export-job-parameters-plugin | 22 | 9 | 0 | 70.97% | 29.03% | 0.00% |
| jenkinsci/spotinst-plugin | 25 | 6 | 0 | 80.65% | 19.35% | 0.00% |
| jfrog/fly-action | 14 | 17 | 0 | 45.16% | 54.84% | 0.00% |
| justachillcoder/binance-captcha-deobfuscator | 13 | 18 | 0 | 41.94% | 58.06% | 0.00% |
| kaltura/chromeless-kdp | 24 | 7 | 0 | 77.42% | 22.58% | 0.00% |
| kusamanetwork/faucet | 29 | 2 | 0 | 93.55% | 6.45% | 0.00% |
| ladieslearningcode/llc-intro-to-python | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| laravel/nova-issues | 29 | 2 | 0 | 93.55% | 6.45% | 0.00% |
| learn-co-students/moving-things-with-javascript-bootcamp-prep-000 | 18 | 13 | 0 | 58.06% | 41.94% | 0.00% |
| littlejohn19/TAI_Lab_1 | 17 | 14 | 0 | 54.84% | 45.16% | 0.00% |
| llvm/llvm-project | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| lovehackintosh/lede | 28 | 3 | 0 | 90.32% | 9.68% | 0.00% |
| m3ntorship/m3ntorship.com | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| magento/tmp-pr-test1 | 14 | 17 | 0 | 45.16% | 54.84% | 0.00% |
| mdaus/nitro | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| mhornstein/Glitters1 | 28 | 3 | 0 | 90.32% | 9.68% | 0.00% |
| microsoft/rural-crowdsourcing-toolkit | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| microsoft/tim-data-investigate-platform | 28 | 3 | 0 | 90.32% | 9.68% | 0.00% |
| microsoft/vscode | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| microsoft/winget-pkgs | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| mopub/mopub-android-sdk | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| muhandojeon/Why-Do-We-Work | 23 | 8 | 0 | 74.19% | 25.81% | 0.00% |
| ngaly277/zoo-management | 21 | 10 | 0 | 67.74% | 32.26% | 0.00% |
| node-honeycomb/node-honeycomb.github.io | 27 | 4 | 0 | 87.10% | 12.90% | 0.00% |
| odoo/odoo | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| ohirofumi/freemarket_sample_54a | 25 | 6 | 0 | 80.65% | 19.35% | 0.00% |
| omegapointnorge/omega-office-booking | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| open-telemetry/opentelemetry-js-contrib | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| openai/codex | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| openbilibili/go-common | 16 | 15 | 0 | 51.61% | 48.39% | 0.00% |
| openjdk/jdk | 25 | 6 | 0 | 80.65% | 19.35% | 0.00% |
| prime-team-aeon/home-survey | 24 | 7 | 0 | 77.42% | 22.58% | 0.00% |
| puppetlabs/install-puppet | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| pytorch/pytorch | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| rancher/refpolicy | 24 | 7 | 0 | 77.42% | 22.58% | 0.00% |
| ratchetphp/Ratchet | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| return42/searxng | 24 | 7 | 0 | 77.42% | 22.58% | 0.00% |
| rizafahmi/awesome-speakers-id | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| rust-lang/rust | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| sailro/EscapeFromTarkov-Trainer | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| schibsted/account-sdk-android-web | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| searchlight/searchlight | 23 | 8 | 0 | 74.19% | 25.81% | 0.00% |
| sfuosdev/swe-resume-evaluator | 25 | 6 | 0 | 80.65% | 19.35% | 0.00% |
| sgl-project/sglang | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| skabanets/function-force | 23 | 8 | 0 | 74.19% | 25.81% | 0.00% |
| solana-labs/token-list | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| souravDgraph/Automation | 24 | 7 | 0 | 77.42% | 22.58% | 0.00% |
| sst/opencode | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| stackabletech/stackablectl | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| stackrox/mishas-operator-index-fork | 13 | 18 | 0 | 41.94% | 58.06% | 0.00% |
| superluis1994/IAmed | 21 | 10 | 0 | 67.74% | 32.26% | 0.00% |
| taikoxyz/taiko-client | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| taozhiyu/TyProAction | 29 | 2 | 0 | 93.55% | 6.45% | 0.00% |
| teamtype/teamtype | 22 | 9 | 0 | 70.97% | 29.03% | 0.00% |
| tenstorrent/tt-metal | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| thecasualcoder/tztail | 29 | 2 | 0 | 93.55% | 6.45% | 0.00% |
| tomasbedrich/home-assistant-hikconnect | 29 | 2 | 0 | 93.55% | 6.45% | 0.00% |
| tripledes/thesheriff | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| trustimaging/stride | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| twitterdev/twitter-leaderboard | 17 | 14 | 0 | 54.84% | 45.16% | 0.00% |
| umrover/mrover-workspace | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| vllm-project/vllm | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| w3c/microdata | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| welfoz/Machi_Koro | 24 | 7 | 0 | 77.42% | 22.58% | 0.00% |
| wonipapa/epg2xml | 29 | 2 | 0 | 93.55% | 6.45% | 0.00% |
| wooncloud/animalcare | 28 | 3 | 0 | 90.32% | 9.68% | 0.00% |
| yoav-zibin/GameBuilder | 29 | 2 | 0 | 93.55% | 6.45% | 0.00% |
| zed-industries/zed | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |
| zencomputersystems/CMS_Analyst | 24 | 7 | 0 | 77.42% | 22.58% | 0.00% |
| zephyrproject-rtos/zephyr | 30 | 1 | 0 | 96.77% | 3.23% | 0.00% |

## 上游不存在最多的指标（404 Top）

| metric | 404_count |
| --- | --- |
| community_openrank | 196 |
| change_requests_reviews | 74 |
| issues_closed | 71 |
| issue_resolution_duration | 70 |
| issues_new | 56 |
| issue_response_time | 55 |
| issue_age | 55 |
| stars | 40 |
| technical_fork | 35 |
| inactive_contributors | 28 |

## 时间跨度（按 metric 与 period_type）

| metric | period_type | min | max | period_count |
| --- | --- | --- | --- | --- |
| activity | month | 2015-01 | 2025-12 | 132 |
| activity | quarter | 2015Q1 | 2025Q4 | 44 |
| activity | year | 2015 | 2025 | 11 |
| attention | month | 2015-01 | 2025-12 | 132 |
| attention | quarter | 2015Q1 | 2025Q4 | 44 |
| attention | year | 2015 | 2025 | 11 |
| bus_factor | month | 2015-01 | 2025-12 | 132 |
| bus_factor | quarter | 2015Q1 | 2025Q4 | 44 |
| bus_factor | year | 2015 | 2025 | 11 |
| change_requests | month | 2015-01 | 2025-12 | 132 |
| change_requests | quarter | 2015Q1 | 2025Q4 | 44 |
| change_requests | year | 2015 | 2025 | 11 |
| change_requests_accepted | month | 2015-01 | 2025-12 | 132 |
| change_requests_accepted | quarter | 2015Q1 | 2025Q4 | 44 |
| change_requests_accepted | year | 2015 | 2025 | 11 |
| change_requests_reviews | month | 2015-01 | 2025-12 | 132 |
| change_requests_reviews | quarter | 2015Q1 | 2025Q4 | 44 |
| change_requests_reviews | year | 2015 | 2025 | 11 |
| code_change_lines_add | month | 2015-01 | 2025-12 | 132 |
| code_change_lines_add | quarter | 2015Q1 | 2025Q4 | 44 |
| code_change_lines_add | year | 2015 | 2025 | 11 |
| code_change_lines_remove | month | 2015-01 | 2025-12 | 132 |
| code_change_lines_remove | quarter | 2015Q1 | 2025Q4 | 44 |
| code_change_lines_remove | year | 2015 | 2025 | 11 |
| code_change_lines_sum | month | 2015-01 | 2025-12 | 132 |
| code_change_lines_sum | quarter | 2015Q1 | 2025Q4 | 44 |
| code_change_lines_sum | year | 2015 | 2025 | 11 |
| contributors | month | 2015-01 | 2025-12 | 132 |
| contributors | quarter | 2015Q1 | 2025Q4 | 44 |
| contributors | year | 2015 | 2025 | 11 |
| inactive_contributors | month | 2015-07 | 2025-12 | 126 |
| inactive_contributors | quarter | 2015Q3 | 2025Q4 | 42 |
| inactive_contributors | year | 2015 | 2025 | 11 |
| issue_comments | month | 2015-01 | 2025-12 | 132 |
| issue_comments | quarter | 2015Q1 | 2025Q4 | 44 |
| issue_comments | year | 2015 | 2025 | 11 |
| issues_closed | month | 2015-01 | 2025-12 | 132 |
| issues_closed | quarter | 2015Q1 | 2025Q4 | 44 |
| issues_closed | year | 2015 | 2025 | 11 |
| issues_new | month | 2015-01 | 2025-12 | 132 |
| issues_new | quarter | 2015Q1 | 2025Q4 | 44 |
| issues_new | year | 2015 | 2025 | 11 |
| new_contributors | month | 2015-01 | 2025-10 | 130 |
| new_contributors | quarter | 2015Q1 | 2025Q4 | 44 |
| new_contributors | year | 2015 | 2025 | 11 |
| openrank | month | 2015-01 | 2025-12 | 132 |
| openrank | quarter | 2015Q1 | 2025Q4 | 44 |
| openrank | year | 2015 | 2025 | 11 |
| participants | month | 2015-01 | 2025-12 | 132 |
| participants | quarter | 2015Q1 | 2025Q4 | 44 |
| participants | year | 2015 | 2025 | 11 |
| stars | month | 2015-01 | 2025-12 | 132 |
| stars | quarter | 2015Q1 | 2025Q4 | 44 |
| stars | year | 2015 | 2025 | 11 |
| technical_fork | month | 2015-01 | 2025-12 | 131 |
| technical_fork | quarter | 2015Q1 | 2025Q4 | 44 |
| technical_fork | year | 2015 | 2025 | 11 |

## period 数分布（按 metric）

| metric | repo_count | min | median | max |
| --- | --- | --- | --- | --- |
| openrank | 195 | 3 | 14 | 187 |
| activity | 195 | 3 | 16 | 187 |
| stars | 156 | 3 | 20 | 187 |
| technical_fork | 161 | 3 | 15 | 186 |
| attention | 174 | 3 | 19 | 187 |
| new_contributors | 171 | 1 | 9 | 185 |
| contributors | 171 | 3 | 16 | 185 |
| inactive_contributors | 164 | 1 | 71 | 179 |
| participants | 195 | 3 | 16 | 187 |
| bus_factor | 194 | 3 | 15 | 187 |
| issues_new | 140 | 3 | 17 | 187 |
| issues_closed | 125 | 3 | 17 | 187 |
| issue_comments | 170 | 3 | 20 | 187 |
| change_requests | 181 | 3 | 16 | 187 |
| change_requests_accepted | 171 | 3 | 16 | 185 |
| change_requests_reviews | 122 | 3 | 13 | 187 |
| code_change_lines_add | 178 | 3 | 18 | 185 |
| code_change_lines_remove | 176 | 3 | 19 | 185 |
| code_change_lines_sum | 179 | 3 | 16 | 185 |

## 缺失率（按 metric）

| metric | repo_total | missing_full | missing_partial | missing_full_ratio | missing_partial_ratio | max_periods |
| --- | --- | --- | --- | --- | --- | --- |
| openrank | 196 | 1 | 185 | 0.51% | 94.39% | 187 |
| community_openrank | 196 | 196 | 0 | 100.00% | 0.00% | 0 |
| activity | 196 | 1 | 185 | 0.51% | 94.39% | 187 |
| activity_details | 196 | 196 | 0 | 100.00% | 0.00% | 0 |
| stars | 196 | 40 | 145 | 20.41% | 73.98% | 187 |
| technical_fork | 196 | 35 | 152 | 17.86% | 77.55% | 186 |
| attention | 196 | 22 | 163 | 11.22% | 83.16% | 187 |
| active_dates_and_times | 196 | 196 | 0 | 100.00% | 0.00% | 0 |
| new_contributors | 196 | 25 | 164 | 12.76% | 83.67% | 185 |
| new_contributors_detail | 196 | 196 | 0 | 100.00% | 0.00% | 0 |
| contributors | 196 | 25 | 163 | 12.76% | 83.16% | 185 |
| contributors_detail | 196 | 196 | 0 | 100.00% | 0.00% | 0 |
| inactive_contributors | 196 | 32 | 154 | 16.33% | 78.57% | 179 |
| participants | 196 | 1 | 185 | 0.51% | 94.39% | 187 |
| bus_factor | 196 | 2 | 184 | 1.02% | 93.88% | 187 |
| bus_factor_detail | 196 | 196 | 0 | 100.00% | 0.00% | 0 |
| issues_new | 196 | 56 | 131 | 28.57% | 66.84% | 187 |
| issues_closed | 196 | 71 | 116 | 36.22% | 59.18% | 187 |
| issue_comments | 196 | 26 | 161 | 13.27% | 82.14% | 187 |
| issue_response_time | 196 | 196 | 0 | 100.00% | 0.00% | 0 |
| issue_resolution_duration | 196 | 196 | 0 | 100.00% | 0.00% | 0 |
| issue_age | 196 | 196 | 0 | 100.00% | 0.00% | 0 |
| change_requests | 196 | 15 | 172 | 7.65% | 87.76% | 187 |
| change_requests_accepted | 196 | 25 | 163 | 12.76% | 83.16% | 185 |
| change_requests_reviews | 196 | 74 | 116 | 37.76% | 59.18% | 187 |
| change_request_response_time | 196 | 196 | 0 | 100.00% | 0.00% | 0 |
| change_request_resolution_duration | 196 | 196 | 0 | 100.00% | 0.00% | 0 |
| change_request_age | 196 | 196 | 0 | 100.00% | 0.00% | 0 |
| code_change_lines_add | 196 | 18 | 169 | 9.18% | 86.22% | 185 |
| code_change_lines_remove | 196 | 20 | 167 | 10.20% | 85.20% | 185 |
| code_change_lines_sum | 196 | 17 | 170 | 8.67% | 86.73% | 185 |

## 异常值概览（按 metric）

| metric | count | negatives | nulls | non_numeric | p01 | p50 | p99 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| openrank | 8310 | 0 | 0 | 0 | 0.2300 | 13.7550 | 5930.1366 |
| activity | 8522 | 0 | 0 | 0 | 0.7200 | 45.2900 | 16913.0817 |
| stars | 7700 | 0 | 0 | 0 | 1.0000 | 43.0000 | 7877.9400 |
| technical_fork | 7134 | 0 | 0 | 0 | 1.0000 | 22.0000 | 2479.7400 |
| attention | 8366 | 0 | 0 | 0 | 1.0000 | 53.0000 | 11416.3500 |
| new_contributors | 4776 | 0 | 0 | 0 | 1.0000 | 9.0000 | 402.7500 |
| contributors | 6093 | 0 | 0 | 0 | 1.0000 | 9.0000 | 797.4800 |
| inactive_contributors | 12796 | 0 | 0 | 0 | 1.0000 | 8.0000 | 3102.5500 |
| participants | 8659 | 0 | 0 | 0 | 1.0000 | 15.0000 | 5177.2600 |
| bus_factor | 8469 | 0 | 0 | 0 | 1.0000 | 9.0000 | 2703.0000 |
| issues_new | 6149 | 0 | 0 | 0 | 1.0000 | 58.0000 | 8124.8000 |
| issues_closed | 5635 | 0 | 0 | 0 | 1.0000 | 70.0000 | 5557.9000 |
| issue_comments | 7370 | 0 | 0 | 0 | 1.0000 | 115.0000 | 71950.1900 |
| change_requests | 7306 | 0 | 0 | 0 | 1.0000 | 27.0000 | 11180.6500 |
| change_requests_accepted | 6093 | 0 | 0 | 0 | 1.0000 | 33.0000 | 9440.3600 |
| change_requests_reviews | 4744 | 0 | 0 | 0 | 1.0000 | 445.0000 | 26362.2400 |
| code_change_lines_add | 7465 | 0 | 0 | 0 | 2.0000 | 15889.0000 | 4677344.5600 |
| code_change_lines_remove | 7323 | 0 | 0 | 0 | 1.0000 | 6210.0000 | 2804089.9400 |
| code_change_lines_sum | 7075 | 760 | 0 | 0 | -92264.5600 | 6737.0000 | 2102928.3800 |
