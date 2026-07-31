# Share Copy

The maintained X-ready source is [X-POST.md](X-POST.md).

## Short version

I reproduced Light Foundry's GLM-5.2-Vision NVFP4 result on my eight GB10
cluster: 1M context, a 1,264,256-token KV pool, 45.98 tok/s at c1, and 115.75
tok/s aggregate at c8.

The fresh 63.6-minute soak passed 1,484/1,484 short requests and all six deep
50K/200K/500K injections.

The repo includes the exact native-SM121 build delta, methodology, failure
record, public result JSON, and sanitized harnesses.
