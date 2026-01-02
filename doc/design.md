# 语言设计

## 需求

1. 它有 15-20 条语法设计；
2. 它足够简单，能提供基本的功能就行了，不要任何过度复杂的语法糖；
3. 它是编译型的；
4. 它是函数式，要支持嵌套函数定义形成闭包（也就是编译期将嵌套声明时用到的环境隐式提出来，变成参数，运行时自动给它传进去），函数可以被传来传去（至少在顶层语法是这样，编译完就不要这样了），但不要跟 haskell 那么晦涩，我希望它能像 lisp 那样简单（你甚至不需要支持运算符，但我希望它的语法美一点，至少 lisp 的 define 语法我觉得很丑，应该加个语法糖，比如 标识符 <- (arg: type, arg: type) -> return_type { xxx };）；
5. 在函数式的基础上，我要假定所有函数都是 constexpr，也就是说，不加任何标注的函数默认无副作用，如果发现有（比如子函数有副作用，就传染），就报错；有副作用的函数必须加标注；有副作用，但程序员不在乎的（比如本来就想只执行一次，或者幂等操作），可以加另外的标注改变编译器行为（但仍然不能改变其有副作用的现实，后面常量展开，编译期计算不应该展开这种函数）；
6. 它要默认支持编译期计算；
7. 它应该编译到一个超简单 ir 上，为了节省工期，要自己写 ir 解释器，不做后端了；
8. 这个 ir 要做 ssa 优化，要做循环不变式外提；
9. 它要有个类型系统（请牢记它是编译型语言，解释执行的是 ir，在一个有栈和堆，提供一堆预定义接口的虚拟机上），要支持通过 typedef，数组（确定数目的同类元素的重复，但我希望实现时允许偶尔不确定数目，比如函数分配栈变量时就能确定数目的情况），结构体（具名或者不具名的），指针（就像 c 那样），引用扩展类型，形成一个类型推导树，支持泛型（可以当作宏来实现，我要额外支持数字（比如数组长度，以便于编译期计算），但别写成跟 cpp 模板那个鬼样子似的，我要它够简单），支持基于类型的函数重载（而且要有 match，就像 cpp 如果没有直接重载相应类型，会通过类型转换构造函数查找能对上的重载）；请你想一套简单又清晰的类型语法；
10. 但是这个类型系统仅用于重载/内存分配，我不想加入难写的语法，比如数组我不希望是 arr: i32[3] <- { 1, 2, 3 }; arr[0];什么的，我希望你直接在编译时，直接在当前作用域下自动生成函数（反正我默认是 constexpr，还能 inline 展开，没什么开销），比如 get: auto <- (index: index*t, arr: i32 * N) -> i32 { /\_ 编译器产生的 ir，直接取一段内存 \*/ }；
11. 它要有一系列魔法函数，至少要支持类型间互相转换的（然后基于它我希望重载能推导）；
12. 整体实现务必最简，要最优雅；

## 语法规则

### 赋值（bind/define）与字面量

```
int_var: i32 = INTEGER_CONSTANT;

float_var: fp32 = -FLOAT_CONSTANT;
float_var: fp32 = FLOAT_CONSTANT;
float_var: fp32 = na;
float_var: fp32 = -inf;

boolean_var: bool = true;

```

#### float style

```
0.0
.0
0.
1.0
1.
.1
114.514
114.514e2
114.514E+2
114.514e-2
1e0
1E10
1e+10
1e-10
0e0
0.0f
1.0L
.5e3
5.e3
1_000.000_1
1_2_3.4_5e6
0x1p0
0x1P0
0x1.0p0
0x1.p0
0x.1p0
0x1.1p1
0x1.1p+1
0x1.1p-1
0x1_2.3_4p5
0XAF.1P10
0x0.1p0
0b1.0p0
0b1.1p1
0b1.p1
0b.1p1
0b1_0.1_1p10
0B101.01e3
0b0.1p0
0o7.0p0
0o7.1p1
0o7.p1
0o.1p1
0o1_2.3_4e5
0O77.01P3
0x1.0
0x1.
0x.1
0b1.1
0b1.
0b.1
0o7.1
0o7.
0o.1
```

#### int style

```antlr
lexer grammar Integer;

/*
 * entry point
 */
INTEGER_CONSTANT
    : DECIMAL_INTEGER SUFFIX?
    | OCTAL_INTEGER   SUFFIX?
    | HEX_INTEGER     SUFFIX?
    | BINARY_INTEGER  SUFFIX?
    ;

/*
 * ---------- decimal ----------
 * 0 or non-zero leading
 */

fragment DECIMAL_INTEGER
    : '0'
    | NONZERO_DIGIT DECIMAL_DIGITS?
    ;

/*
 * ---------- octal ----------
 * leading 0, digits 0-7
 */

fragment OCTAL_INTEGER
    : '0' OCTAL_DIGITS
    ;

/*
 * ---------- hexadecimal ----------
 */

fragment HEX_INTEGER
    : HEX_PREFIX HEX_DIGITS
    ;

/*
 * ---------- binary (modern extension) ----------
 */

fragment BINARY_INTEGER
    : BIN_PREFIX BIN_DIGITS
    ;

/*
 * ---------- digit sequences with underscore ----------
 * underscore cannot be leading or trailing
 */

fragment DECIMAL_DIGITS
    : DECIMAL_DIGIT ('_'? DECIMAL_DIGIT)*
    ;

fragment OCTAL_DIGITS
    : OCTAL_DIGIT ('_'? OCTAL_DIGIT)*
    ;

fragment HEX_DIGITS
    : HEX_DIGIT ('_'? HEX_DIGIT)*
    ;

fragment BIN_DIGITS
    : BIN_DIGIT ('_'? BIN_DIGIT)*
    ;

/*
 * ---------- suffix ----------
 * compatible with C: u, l, ll (any order, any case)
 */

fragment SUFFIX
    : UNSIGNED_SUFFIX LONG_SUFFIX?
    | LONG_SUFFIX UNSIGNED_SUFFIX?
    ;

fragment UNSIGNED_SUFFIX
    : [uU]
    ;

fragment LONG_SUFFIX
    : [lL] [lL]?
    ;

/*
 * ---------- basic ----------
 */

fragment NONZERO_DIGIT
    : [1-9]
    ;

fragment DECIMAL_DIGIT
    : [0-9]
    ;

fragment OCTAL_DIGIT
    : [0-7]
    ;

fragment HEX_DIGIT
    : [0-9a-fA-F]
    ;

fragment BIN_DIGIT
    : [01]
    ;

fragment HEX_PREFIX
    : '0' [xX]
    ;

fragment BIN_PREFIX
    : '0' [bB]
    ;
```
