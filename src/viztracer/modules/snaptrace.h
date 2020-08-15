#ifndef __SNAPTRACE_H__
#define __SNAPTRACE_H__

#define SNAPTRACE_MAX_STACK_DEPTH (1 << 0)
#define SNAPTRACE_INCLUDE_FILES (1 << 1)
#define SNAPTRACE_EXCLUDE_FILES (1 << 2)
#define SNAPTRACE_IGNORE_C_FUNCTION (1 << 3)

#define SET_FLAG(reg, flag) ((reg) |= (flag))
#define UNSET_FLAG(reg, flag) ((reg) &= (~(flag)))

#define CHECK_FLAG(reg, flag) (((reg) & (flag)) != 0) 

#endif