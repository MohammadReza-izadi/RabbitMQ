sudo docker rm rabbit-1 rabbit-2 rabbit-3 rabbit-4

sudo docker start rabbit-4 rabbit-3 rabbit-2 rabbit-1



# Test1    - Durable with docker rm

    Remove container with rm and create with compose

        - sudo docker stop rabbit-1 rabbit-2 rabbit-3 rabbit-4
        - sudo docker rm rabbit-1 rabbit-2 rabbit-3 rabbit-4
    All of data in removed

# Test2  - Restore

    Restore Export definitions
        - Just Queue in Restored