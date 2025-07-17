2025-07-17T10:30:36.9369499Z Current runner version: '2.326.0'
2025-07-17T10:30:36.9407400Z ##[group]Operating System
2025-07-17T10:30:36.9408683Z Ubuntu
2025-07-17T10:30:36.9409590Z 24.04.2
2025-07-17T10:30:36.9410390Z LTS
2025-07-17T10:30:36.9411153Z ##[endgroup]
2025-07-17T10:30:36.9412091Z ##[group]Runner Image
2025-07-17T10:30:36.9413104Z Image: ubuntu-24.04
2025-07-17T10:30:36.9414086Z Version: 20250713.1.0
2025-07-17T10:30:36.9416217Z Included Software: https://github.com/actions/runner-images/blob/ubuntu24/20250713.1/images/ubuntu/Ubuntu2404-Readme.md
2025-07-17T10:30:36.9418833Z Image Release: https://github.com/actions/runner-images/releases/tag/ubuntu24%2F20250713.1
2025-07-17T10:30:36.9420433Z ##[endgroup]
2025-07-17T10:30:36.9421302Z ##[group]Runner Image Provisioner
2025-07-17T10:30:36.9422523Z 2.0.449.1
2025-07-17T10:30:36.9423314Z ##[endgroup]
2025-07-17T10:30:36.9425366Z ##[group]GITHUB_TOKEN Permissions
2025-07-17T10:30:36.9428032Z Contents: write
2025-07-17T10:30:36.9428969Z Metadata: read
2025-07-17T10:30:36.9430202Z ##[endgroup]
2025-07-17T10:30:36.9433682Z Secret source: Actions
2025-07-17T10:30:36.9435125Z Prepare workflow directory
2025-07-17T10:30:37.0190795Z Prepare all required actions
2025-07-17T10:30:37.0247338Z Getting action download info
2025-07-17T10:30:37.4362443Z ##[group]Download immutable action package 'actions/checkout@v4'
2025-07-17T10:30:37.4363608Z Version: 4.2.2
2025-07-17T10:30:37.4364699Z Digest: sha256:ccb2698953eaebd21c7bf6268a94f9c26518a7e38e27e0b83c1fe1ad049819b1
2025-07-17T10:30:37.4366375Z Source commit SHA: 11bd71901bbe5b1630ceea73d27597364c9af683
2025-07-17T10:30:37.4367767Z ##[endgroup]
2025-07-17T10:30:37.5285208Z ##[group]Download immutable action package 'actions/setup-python@v5'
2025-07-17T10:30:37.5286055Z Version: 5.6.0
2025-07-17T10:30:37.5286925Z Digest: sha256:0b35a0c11c97499e4e0576589036d450b9f5f9da74b7774225b3614b57324404
2025-07-17T10:30:37.5287956Z Source commit SHA: a26af69be951a213d495a4c3e4e4022e16d87065
2025-07-17T10:30:37.5288685Z ##[endgroup]
2025-07-17T10:30:37.8869445Z Complete job name: alert
2025-07-17T10:30:37.9583923Z ##[group]Run actions/checkout@v4
2025-07-17T10:30:37.9585046Z with:
2025-07-17T10:30:37.9585510Z   repository: kuywata/testwaternew05
2025-07-17T10:30:37.9586253Z   token: ***
2025-07-17T10:30:37.9586671Z   ssh-strict: true
2025-07-17T10:30:37.9587112Z   ssh-user: git
2025-07-17T10:30:37.9587556Z   persist-credentials: true
2025-07-17T10:30:37.9588047Z   clean: true
2025-07-17T10:30:37.9588482Z   sparse-checkout-cone-mode: true
2025-07-17T10:30:37.9589019Z   fetch-depth: 1
2025-07-17T10:30:37.9589450Z   fetch-tags: false
2025-07-17T10:30:37.9589893Z   show-progress: true
2025-07-17T10:30:37.9590333Z   lfs: false
2025-07-17T10:30:37.9590737Z   submodules: false
2025-07-17T10:30:37.9591182Z   set-safe-directory: true
2025-07-17T10:30:37.9591896Z env:
2025-07-17T10:30:37.9592489Z   GITHUB_TOKEN: ***
2025-07-17T10:30:37.9594214Z   LINE_CHANNEL_ACCESS_TOKEN: ***
2025-07-17T10:30:37.9594717Z ##[endgroup]
2025-07-17T10:30:38.1357044Z Syncing repository: kuywata/testwaternew05
2025-07-17T10:30:38.1359428Z ##[group]Getting Git version info
2025-07-17T10:30:38.1360518Z Working directory is '/home/runner/work/testwaternew05/testwaternew05'
2025-07-17T10:30:38.1362057Z [command]/usr/bin/git version
2025-07-17T10:30:38.1406930Z git version 2.50.1
2025-07-17T10:30:38.1434567Z ##[endgroup]
2025-07-17T10:30:38.1448744Z Temporarily overriding HOME='/home/runner/work/_temp/4db6886e-e090-41d1-ba00-b81833e64638' before making global git config changes
2025-07-17T10:30:38.1451084Z Adding repository directory to the temporary git global config as a safe directory
2025-07-17T10:30:38.1461542Z [command]/usr/bin/git config --global --add safe.directory /home/runner/work/testwaternew05/testwaternew05
2025-07-17T10:30:38.1499456Z Deleting the contents of '/home/runner/work/testwaternew05/testwaternew05'
2025-07-17T10:30:38.1502876Z ##[group]Initializing the repository
2025-07-17T10:30:38.1507629Z [command]/usr/bin/git init /home/runner/work/testwaternew05/testwaternew05
2025-07-17T10:30:38.1566586Z hint: Using 'master' as the name for the initial branch. This default branch name
2025-07-17T10:30:38.1569648Z hint: is subject to change. To configure the initial branch name to use in all
2025-07-17T10:30:38.1571700Z hint: of your new repositories, which will suppress this warning, call:
2025-07-17T10:30:38.1573158Z hint:
2025-07-17T10:30:38.1574387Z hint: 	git config --global init.defaultBranch <name>
2025-07-17T10:30:38.1576032Z hint:
2025-07-17T10:30:38.1577227Z hint: Names commonly chosen instead of 'master' are 'main', 'trunk' and
2025-07-17T10:30:38.1579241Z hint: 'development'. The just-created branch can be renamed via this command:
2025-07-17T10:30:38.1581322Z hint:
2025-07-17T10:30:38.1582150Z hint: 	git branch -m <name>
2025-07-17T10:30:38.1583143Z hint:
2025-07-17T10:30:38.1584545Z hint: Disable this message with "git config set advice.defaultBranchName false"
2025-07-17T10:30:38.1587439Z Initialized empty Git repository in /home/runner/work/testwaternew05/testwaternew05/.git/
2025-07-17T10:30:38.1591412Z [command]/usr/bin/git remote add origin https://github.com/kuywata/testwaternew05
2025-07-17T10:30:38.1615641Z ##[endgroup]
2025-07-17T10:30:38.1617233Z ##[group]Disabling automatic garbage collection
2025-07-17T10:30:38.1618986Z [command]/usr/bin/git config --local gc.auto 0
2025-07-17T10:30:38.1649281Z ##[endgroup]
2025-07-17T10:30:38.1650726Z ##[group]Setting up auth
2025-07-17T10:30:38.1655702Z [command]/usr/bin/git config --local --name-only --get-regexp core\.sshCommand
2025-07-17T10:30:38.1686690Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
2025-07-17T10:30:38.1980543Z [command]/usr/bin/git config --local --name-only --get-regexp http\.https\:\/\/github\.com\/\.extraheader
2025-07-17T10:30:38.2010973Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'http\.https\:\/\/github\.com\/\.extraheader' && git config --local --unset-all 'http.https://github.com/.extraheader' || :"
2025-07-17T10:30:38.2237962Z [command]/usr/bin/git config --local http.https://github.com/.extraheader AUTHORIZATION: basic ***
2025-07-17T10:30:38.2279354Z ##[endgroup]
2025-07-17T10:30:38.2281485Z ##[group]Fetching the repository
2025-07-17T10:30:38.2290237Z [command]/usr/bin/git -c protocol.version=2 fetch --no-tags --prune --no-recurse-submodules --depth=1 origin +f96934d50004875eb2d20715e8ea73eb9330e28d:refs/remotes/origin/main
2025-07-17T10:30:38.4065445Z From https://github.com/kuywata/testwaternew05
2025-07-17T10:30:38.4067196Z  * [new ref]         f96934d50004875eb2d20715e8ea73eb9330e28d -> origin/main
2025-07-17T10:30:38.4093303Z ##[endgroup]
2025-07-17T10:30:38.4095085Z ##[group]Determining the checkout info
2025-07-17T10:30:38.4096800Z ##[endgroup]
2025-07-17T10:30:38.4101621Z [command]/usr/bin/git sparse-checkout disable
2025-07-17T10:30:38.4143273Z [command]/usr/bin/git config --local --unset-all extensions.worktreeConfig
2025-07-17T10:30:38.4173719Z ##[group]Checking out the ref
2025-07-17T10:30:38.4178376Z [command]/usr/bin/git checkout --progress --force -B main refs/remotes/origin/main
2025-07-17T10:30:38.4225084Z Switched to a new branch 'main'
2025-07-17T10:30:38.4227745Z branch 'main' set up to track 'origin/main'.
2025-07-17T10:30:38.4235215Z ##[endgroup]
2025-07-17T10:30:38.4269515Z [command]/usr/bin/git log -1 --format=%H
2025-07-17T10:30:38.4291659Z f96934d50004875eb2d20715e8ea73eb9330e28d
2025-07-17T10:30:38.4583646Z ##[group]Run actions/setup-python@v5
2025-07-17T10:30:38.4584738Z with:
2025-07-17T10:30:38.4585620Z   python-version: 3.x
2025-07-17T10:30:38.4586514Z   check-latest: false
2025-07-17T10:30:38.4587644Z   token: ***
2025-07-17T10:30:38.4588448Z   update-environment: true
2025-07-17T10:30:38.4589414Z   allow-prereleases: false
2025-07-17T10:30:38.4590345Z   freethreaded: false
2025-07-17T10:30:38.4591183Z env:
2025-07-17T10:30:38.4592166Z   GITHUB_TOKEN: ***
2025-07-17T10:30:38.4596035Z   LINE_CHANNEL_ACCESS_TOKEN: ***
2025-07-17T10:30:38.4597219Z ##[endgroup]
2025-07-17T10:30:38.6243348Z ##[group]Installed versions
2025-07-17T10:30:38.6297907Z Successfully set up CPython (3.13.5)
2025-07-17T10:30:38.6300323Z ##[endgroup]
2025-07-17T10:30:38.6431628Z ##[group]Run pip install -r requirements.txt
2025-07-17T10:30:38.6432940Z [36;1mpip install -r requirements.txt[0m
2025-07-17T10:30:38.6468373Z shell: /usr/bin/bash -e {0}
2025-07-17T10:30:38.6469289Z env:
2025-07-17T10:30:38.6470507Z   GITHUB_TOKEN: ***
2025-07-17T10:30:38.6474750Z   LINE_CHANNEL_ACCESS_TOKEN: ***
2025-07-17T10:30:38.6476311Z   pythonLocation: /opt/hostedtoolcache/Python/3.13.5/x64
2025-07-17T10:30:38.6478146Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.13.5/x64/lib/pkgconfig
2025-07-17T10:30:38.6480051Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.13.5/x64
2025-07-17T10:30:38.6481501Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.13.5/x64
2025-07-17T10:30:38.6483060Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.13.5/x64
2025-07-17T10:30:38.6484578Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.13.5/x64/lib
2025-07-17T10:30:38.6485945Z ##[endgroup]
2025-07-17T10:30:41.2500324Z Collecting requests (from -r requirements.txt (line 1))
2025-07-17T10:30:41.2968433Z   Downloading requests-2.32.4-py3-none-any.whl.metadata (4.9 kB)
2025-07-17T10:30:41.3205827Z Collecting beautifulsoup4 (from -r requirements.txt (line 2))
2025-07-17T10:30:41.3278779Z   Downloading beautifulsoup4-4.13.4-py3-none-any.whl.metadata (3.8 kB)
2025-07-17T10:30:41.3731356Z Collecting pytz (from -r requirements.txt (line 3))
2025-07-17T10:30:41.3805423Z   Downloading pytz-2025.2-py2.py3-none-any.whl.metadata (22 kB)
2025-07-17T10:30:41.4225877Z Collecting selenium (from -r requirements.txt (line 4))
2025-07-17T10:30:41.4297230Z   Downloading selenium-4.34.2-py3-none-any.whl.metadata (7.5 kB)
2025-07-17T10:30:41.5113888Z Collecting charset_normalizer<4,>=2 (from requests->-r requirements.txt (line 1))
2025-07-17T10:30:41.5185799Z   Downloading charset_normalizer-3.4.2-cp313-cp313-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (35 kB)
2025-07-17T10:30:41.5437387Z Collecting idna<4,>=2.5 (from requests->-r requirements.txt (line 1))
2025-07-17T10:30:41.5506357Z   Downloading idna-3.10-py3-none-any.whl.metadata (10 kB)
2025-07-17T10:30:41.5839592Z Collecting urllib3<3,>=1.21.1 (from requests->-r requirements.txt (line 1))
2025-07-17T10:30:41.5909167Z   Downloading urllib3-2.5.0-py3-none-any.whl.metadata (6.5 kB)
2025-07-17T10:30:41.6171270Z Collecting certifi>=2017.4.17 (from requests->-r requirements.txt (line 1))
2025-07-17T10:30:41.6240365Z   Downloading certifi-2025.7.14-py3-none-any.whl.metadata (2.4 kB)
2025-07-17T10:30:41.6479712Z Collecting soupsieve>1.2 (from beautifulsoup4->-r requirements.txt (line 2))
2025-07-17T10:30:41.6552552Z   Downloading soupsieve-2.7-py3-none-any.whl.metadata (4.6 kB)
2025-07-17T10:30:41.6782209Z Collecting typing-extensions>=4.0.0 (from beautifulsoup4->-r requirements.txt (line 2))
2025-07-17T10:30:41.6858160Z   Downloading typing_extensions-4.14.1-py3-none-any.whl.metadata (3.0 kB)
2025-07-17T10:30:41.7161681Z Collecting trio~=0.30.0 (from selenium->-r requirements.txt (line 4))
2025-07-17T10:30:41.7232938Z   Downloading trio-0.30.0-py3-none-any.whl.metadata (8.5 kB)
2025-07-17T10:30:41.7411797Z Collecting trio-websocket~=0.12.2 (from selenium->-r requirements.txt (line 4))
2025-07-17T10:30:41.7480518Z   Downloading trio_websocket-0.12.2-py3-none-any.whl.metadata (5.1 kB)
2025-07-17T10:30:41.7806927Z Collecting websocket-client~=1.8.0 (from selenium->-r requirements.txt (line 4))
2025-07-17T10:30:41.7878686Z   Downloading websocket_client-1.8.0-py3-none-any.whl.metadata (8.0 kB)
2025-07-17T10:30:41.8100701Z Collecting attrs>=23.2.0 (from trio~=0.30.0->selenium->-r requirements.txt (line 4))
2025-07-17T10:30:41.8170061Z   Downloading attrs-25.3.0-py3-none-any.whl.metadata (10 kB)
2025-07-17T10:30:41.8422079Z Collecting sortedcontainers (from trio~=0.30.0->selenium->-r requirements.txt (line 4))
2025-07-17T10:30:41.8493540Z   Downloading sortedcontainers-2.4.0-py2.py3-none-any.whl.metadata (10 kB)
2025-07-17T10:30:41.8641262Z Collecting outcome (from trio~=0.30.0->selenium->-r requirements.txt (line 4))
2025-07-17T10:30:41.8711686Z   Downloading outcome-1.3.0.post0-py2.py3-none-any.whl.metadata (2.6 kB)
2025-07-17T10:30:41.8852931Z Collecting sniffio>=1.3.0 (from trio~=0.30.0->selenium->-r requirements.txt (line 4))
2025-07-17T10:30:41.8923207Z   Downloading sniffio-1.3.1-py3-none-any.whl.metadata (3.9 kB)
2025-07-17T10:30:41.9134635Z Collecting wsproto>=0.14 (from trio-websocket~=0.12.2->selenium->-r requirements.txt (line 4))
2025-07-17T10:30:41.9206496Z   Downloading wsproto-1.2.0-py3-none-any.whl.metadata (5.6 kB)
2025-07-17T10:30:41.9392439Z Collecting pysocks!=1.5.7,<2.0,>=1.5.6 (from urllib3[socks]~=2.5.0->selenium->-r requirements.txt (line 4))
2025-07-17T10:30:41.9466100Z   Downloading PySocks-1.7.1-py3-none-any.whl.metadata (13 kB)
2025-07-17T10:30:41.9852459Z Collecting h11<1,>=0.9.0 (from wsproto>=0.14->trio-websocket~=0.12.2->selenium->-r requirements.txt (line 4))
2025-07-17T10:30:41.9931160Z   Downloading h11-0.16.0-py3-none-any.whl.metadata (8.3 kB)
2025-07-17T10:30:42.0094301Z Downloading requests-2.32.4-py3-none-any.whl (64 kB)
2025-07-17T10:30:42.0201654Z Downloading charset_normalizer-3.4.2-cp313-cp313-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (148 kB)
2025-07-17T10:30:42.0356180Z Downloading idna-3.10-py3-none-any.whl (70 kB)
2025-07-17T10:30:42.0454313Z Downloading urllib3-2.5.0-py3-none-any.whl (129 kB)
2025-07-17T10:30:42.0582619Z Downloading beautifulsoup4-4.13.4-py3-none-any.whl (187 kB)
2025-07-17T10:30:42.0689769Z Downloading pytz-2025.2-py2.py3-none-any.whl (509 kB)
2025-07-17T10:30:42.0852459Z Downloading selenium-4.34.2-py3-none-any.whl (9.4 MB)
2025-07-17T10:30:42.1373500Z    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.4/9.4 MB 190.2 MB/s eta 0:00:00
2025-07-17T10:30:42.1444655Z Downloading trio-0.30.0-py3-none-any.whl (499 kB)
2025-07-17T10:30:42.1558336Z Downloading trio_websocket-0.12.2-py3-none-any.whl (21 kB)
2025-07-17T10:30:42.1652129Z Downloading typing_extensions-4.14.1-py3-none-any.whl (43 kB)
2025-07-17T10:30:42.1748451Z Downloading PySocks-1.7.1-py3-none-any.whl (16 kB)
2025-07-17T10:30:42.1991256Z Downloading websocket_client-1.8.0-py3-none-any.whl (58 kB)
2025-07-17T10:30:42.2087384Z Downloading attrs-25.3.0-py3-none-any.whl (63 kB)
2025-07-17T10:30:42.2183069Z Downloading certifi-2025.7.14-py3-none-any.whl (162 kB)
2025-07-17T10:30:42.2277191Z Downloading outcome-1.3.0.post0-py2.py3-none-any.whl (10 kB)
2025-07-17T10:30:42.2370681Z Downloading sniffio-1.3.1-py3-none-any.whl (10 kB)
2025-07-17T10:30:42.2463150Z Downloading soupsieve-2.7-py3-none-any.whl (36 kB)
2025-07-17T10:30:42.2558330Z Downloading wsproto-1.2.0-py3-none-any.whl (24 kB)
2025-07-17T10:30:42.2649067Z Downloading h11-0.16.0-py3-none-any.whl (37 kB)
2025-07-17T10:30:42.2748338Z Downloading sortedcontainers-2.4.0-py2.py3-none-any.whl (29 kB)
2025-07-17T10:30:42.3479427Z Installing collected packages: sortedcontainers, pytz, websocket-client, urllib3, typing-extensions, soupsieve, sniffio, pysocks, idna, h11, charset_normalizer, certifi, attrs, wsproto, requests, outcome, beautifulsoup4, trio, trio-websocket, selenium
2025-07-17T10:30:44.2508234Z 
2025-07-17T10:30:44.2537393Z Successfully installed attrs-25.3.0 beautifulsoup4-4.13.4 certifi-2025.7.14 charset_normalizer-3.4.2 h11-0.16.0 idna-3.10 outcome-1.3.0.post0 pysocks-1.7.1 pytz-2025.2 requests-2.32.4 selenium-4.34.2 sniffio-1.3.1 sortedcontainers-2.4.0 soupsieve-2.7 trio-0.30.0 trio-websocket-0.12.2 typing-extensions-4.14.1 urllib3-2.5.0 websocket-client-1.8.0 wsproto-1.2.0
2025-07-17T10:30:44.4120022Z ##[group]Run python inburi_bridge_alert.py
2025-07-17T10:30:44.4120365Z [36;1mpython inburi_bridge_alert.py[0m
2025-07-17T10:30:44.4150502Z shell: /usr/bin/bash -e {0}
2025-07-17T10:30:44.4150744Z env:
2025-07-17T10:30:44.4151401Z   GITHUB_TOKEN: ***
2025-07-17T10:30:44.4152329Z   LINE_CHANNEL_ACCESS_TOKEN: ***
2025-07-17T10:30:44.4152639Z   pythonLocation: /opt/hostedtoolcache/Python/3.13.5/x64
2025-07-17T10:30:44.4153262Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.13.5/x64/lib/pkgconfig
2025-07-17T10:30:44.4153682Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.13.5/x64
2025-07-17T10:30:44.4154035Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.13.5/x64
2025-07-17T10:30:44.4154388Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.13.5/x64
2025-07-17T10:30:44.4154741Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.13.5/x64/lib
2025-07-17T10:30:44.4155230Z ##[endgroup]
2025-07-17T10:30:46.1217767Z --- เริ่มทำงาน (API Version) ---
2025-07-17T10:30:46.1218378Z ข้อมูลเก่า: 6.21
2025-07-17T10:30:46.1219548Z --> ❌ เกิดข้อผิดพลาด: 404 Client Error: Not Found for url: https://api-v3.thaiwater.net/api/v1/stations/tele_station/C.2?include=basin,sub_basin,province,amphoe,tambol,rid_center,agency
2025-07-17T10:30:46.1220585Z --- จบการทำงานเพราะดึงข้อมูลใหม่ไม่ได้ ---
2025-07-17T10:30:46.1479274Z ##[group]Run git config --local user.name  "GitHub Action"
2025-07-17T10:30:46.1479715Z [36;1mgit config --local user.name  "GitHub Action"[0m
2025-07-17T10:30:46.1480070Z [36;1mgit config --local user.email "action@github.com"[0m
2025-07-17T10:30:46.1480388Z [36;1mgit add inburi_bridge_data.json[0m
2025-07-17T10:30:46.1480656Z [36;1mgit diff --staged --quiet || ([0m
2025-07-17T10:30:46.1480992Z [36;1m  git commit -m "Update river level data (API)" && git push[0m
2025-07-17T10:30:46.1481303Z [36;1m)[0m
2025-07-17T10:30:46.1510243Z shell: /usr/bin/bash -e {0}
2025-07-17T10:30:46.1510475Z env:
2025-07-17T10:30:46.1510855Z   GITHUB_TOKEN: ***
2025-07-17T10:30:46.1511759Z   LINE_CHANNEL_ACCESS_TOKEN: ***
2025-07-17T10:30:46.1512066Z   pythonLocation: /opt/hostedtoolcache/Python/3.13.5/x64
2025-07-17T10:30:46.1512460Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.13.5/x64/lib/pkgconfig
2025-07-17T10:30:46.1512905Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.13.5/x64
2025-07-17T10:30:46.1513252Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.13.5/x64
2025-07-17T10:30:46.1513602Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.13.5/x64
2025-07-17T10:30:46.1513948Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.13.5/x64/lib
2025-07-17T10:30:46.1514240Z ##[endgroup]
2025-07-17T10:30:46.1695752Z Post job cleanup.
2025-07-17T10:30:46.3301287Z Post job cleanup.
2025-07-17T10:30:46.4233729Z [command]/usr/bin/git version
2025-07-17T10:30:46.4270089Z git version 2.50.1
2025-07-17T10:30:46.4314439Z Temporarily overriding HOME='/home/runner/work/_temp/58093f2a-5f4a-445c-b43c-4eaefd03a365' before making global git config changes
2025-07-17T10:30:46.4315988Z Adding repository directory to the temporary git global config as a safe directory
2025-07-17T10:30:46.4321371Z [command]/usr/bin/git config --global --add safe.directory /home/runner/work/testwaternew05/testwaternew05
2025-07-17T10:30:46.4358061Z [command]/usr/bin/git config --local --name-only --get-regexp core\.sshCommand
2025-07-17T10:30:46.4391799Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
2025-07-17T10:30:46.4624240Z [command]/usr/bin/git config --local --name-only --get-regexp http\.https\:\/\/github\.com\/\.extraheader
2025-07-17T10:30:46.4644537Z http.https://github.com/.extraheader
2025-07-17T10:30:46.4656850Z [command]/usr/bin/git config --local --unset-all http.https://github.com/.extraheader
2025-07-17T10:30:46.4687629Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'http\.https\:\/\/github\.com\/\.extraheader' && git config --local --unset-all 'http.https://github.com/.extraheader' || :"
2025-07-17T10:30:46.5013045Z Cleaning up orphan processes
