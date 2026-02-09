# Task Router - Flow

```
                        User Input
                            |
                            v
                   +----------------+
                   |   classifier   |
                   |  (LLM call)    |
                   |                |
                   |  returns:      |
                   |  category +    |
                   |  confidence    |
                   +----------------+
                            |
                            v
                   +----------------+
                   |   validate     |
                   |                |
                   |  confidence    |
                   |  < 0.6?        |
                   |  -> "unclear"  |
                   +----------------+
                            |
                            v
                   +----------------+
                   | validation     |
                   | route          |
                   +----------------+
                      /    |     \
                     /     |      \
              unclear &    |       \
            retries < 2    |        \
                  /        |         \
                 v         v          v
            +---------+  RETRY   +---------+
            |         |    |     |         |
            v         v    |     v         v
        +------+  +------+|  +-------+  +------+
        | math |  | text | |  |clarify|  |      |
        | node |  | node | |  | node  |  |      |
        +------+  +------+ |  +-------+  |      |
            |         |    |      |       |      |
            v         v    |      v       |      |
          END       END    |    END       |      |
                           |              |      |
                           +---> back to classifier
                                 (max 2 attempts)


RETRY LOGIC:
============

  classifier -----> validate -----> route
       ^                              |
       |                              |
       +--- retry (if unclear &  <----+
             retries < 2)

  attempt 1: classify -> validate -> unclear + retries=1 -> RETRY
  attempt 2: classify -> validate -> unclear + retries=2 -> clarify -> END


CONTINUATION LOGIC (no retry needed):
=====================================

  classifier -----> validate -----> route -----> handler -----> END

  "what is 2+2"       confidence    "math"       math_node     solved
                       >= 0.6                     (LLM call)

  "explain docker"    confidence    "text"       text_node     explained
                       >= 0.6                     (LLM call)


STATE flowing through the graph:
================================

  {
    user_input:  "what is 2+2"     <-- never changes
    task_type:   "" -> "math"      <-- set by classifier, checked by validate
    confidence:  0.0 -> 0.95       <-- set by classifier, checked by validate
    retries:     0 -> 1            <-- incremented each classify attempt
    result:      "" -> "2+2 = 4"   <-- set by handler node
  }
```
