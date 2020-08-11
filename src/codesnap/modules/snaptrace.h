#ifndef __SNAPTRACE_H__
#define __SNAPTRACE_H__

#define SNAPTRACE_MAX_STACK_DEPTH 0

#define SET_FLAG(reg, flag) ((reg) |= (1<<(flag)))
#define UNSET_FLAG(reg, flag) ((reg) &= (~(1<<(flag))))

#define CHECK_FLAG(reg, flag) (((reg) & (1<<(flag))) != 0) 

#endif