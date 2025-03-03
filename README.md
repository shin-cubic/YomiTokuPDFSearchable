# YomiTokuPDFSearchable
YomiTokuを利用してPDFを検索可能にします

## 使い方
[https://moji.or.jp/ipafont/ipaex00401/](https://moji.or.jp/ipafont/ipaex00401/)からIPAex明朝とIPAexゴシックのフォントファイル（TTFファイル）の両方がまとめて入ったZIPファイルをダウンロード、解凍し、同一フォルダ内に入れてください
```
pip install -r requirements.txt
```
```
python createsearchablepdf.py input.pdf output.pdf
```

## その他
YomiTokuを利用してOCRを行っているため、GPUを利用できる環境がベストだが、意外とCPUでも動作する。
## Auther
[https://glass-lab.net](https://glass-lab.net)
