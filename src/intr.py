INTRINSIC = [
    # ===== type atoms =====
    'typ',        # Type 本身的类型（Type of Type）
    'symbol',     # 结构字段 key，仅用于类型结构
    'ptr',        # 指针宽度整数（target dependent）

    'i8', 'u8',   # 8-bit integer
    'i16', 'u16', # 16-bit integer
    'i32', 'u32', # 32-bit integer
    'i64', 'u64', # 64-bit integer
    'i128','u128',# 128-bit integer

    'f32', 'f64', # floating point
    'bool',       # boolean
    'uint',       # uint
    'null_t',     # null type

    # ===== type constructors (affect type id) =====
    'join!',      # join!((a:T1),(b:T2)) -> (a: T1, b: T2)
    'arr!',       # arr!(T, len|...) -> array type
    'union!',     # union!(T, K...) -> union type
    'fn!',        # fn!(params, ret, anno: !default(!arr(symbol), ...), ()) -> function type
    'opaque!',    # opaque!(T) -> new opaque type (new type id)

    # ===== type destruct / reflection (no new type id) =====
    'split!',    # ~tuple!(T) -> field list
    '~arr!',      # ~arr!(T) -> (elem_type, len)
    '~union!',    # ~union!(T) -> field list
    '~fn!',       # ~fn!(T) -> (params, ret, anno)
    '~opaque!',   # ~opaque!(T) -> underlying type (compile-time only)

    # ===== type relation / predicate =====
    'eq!',        # eq!(T1, T2) -> bool (ignore default)
    'has!',       # has!(T, symbol|number) -> bool
    'fn?',  # callable!(T) -> bool
    'opaque?',    # opaque?(T) -> bool

    # ===== type structural edit =====
    'add!',       # add!(T, symbol, T2) -> add field
    'rm!',        # rm!(T, symbol) -> remove field

    # ===== parameter / default behavior =====
    'default!',   # default!(T, const) -> TypeLike with default value
    'strip!',     # strip!(TypeLike) -> raw Type (remove default)

    # ===== compile-time query / control =====
    'if!',        # if!(cond, then, else) -> compile-time branch
    'loop!'       # loop!(fn, first_expr) -> unit, fn := (expr: T): (expr: T, flag: !default(bool, false))
    'typeof!',    # typeof!(expr) -> typ
    'sizeof!',    # sizeof!(typ) -> ptr
    'offsetof!',  # offsetof!(T, symbol|number) -> ptr
    'get!',       # get!(expr: T, key: symbol|index, offset: !default(ptr, 0)) -> K
    'as!',        # as!(expr: T, K: typ) -> K

    # ===== operators (ctfe + runtime) =====
    '+', '-', '*', '/', '%',          # arithmetic
    '&', '|', '^',                    # bitwise
    '<<', '>>',                       # shift
    '==', '!=', '<', '<=', '>', '>=',  # comparison
    '!', '&&', '||',                  # logical

    # ===== special type parameter =====
    '...',        # unknown / variadic type or const parameter
]
