rm test/*.out

for f in test/*; do
    [ -f "$f" ] || continue
    PYTHONUTF8=1 python bin/pipeline.py "$f" -o "${f%.*}.${f##*.}.out" > "${f%.*}.${f##*.}.out"
done

rm test/*.out.out