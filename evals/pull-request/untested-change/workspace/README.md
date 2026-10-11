# slugkit

```sh
bin/slugify "Hello, World!"            # hello-world
bin/slugify --max-length 8 "Hello big world"   # hello
```

`--max-length N` truncates the slug to at most N characters, cutting at the
last hyphen at or before N so no word is split.

Run the tests with `test/run.sh`.
