# RabbitMQ

# Config Doc
    Variable:
        - https://www.rabbitmq.com/configure.html#supported-environment-variables
    Config:
        - https://www.rabbitmq.com/configure.html#supported-environment-variables
    Clustring:
        - https://www.rabbitmq.com/clustering.html#cluster-formation-requirements
    
# Supports Serveral messaging protocols

    - AMQP 0-9-1
    - STOMP 1.0 through 1.2
    - MQTT 3.1.1
    - AMQP 1.0



# Elments of a messaging System

    - Message

    - Producer
    - Consumer

    - Broker/Exchange        
    - Router
    - Queue

    - Connection
    - Channel


# Attributes of a message

    - Routing Key: single or multiple words that are used when distributing a message to the queues.

    - Headers: Key-value used for routing message and passing additional information.

    - Payload: actual data

    - Publishing Timestamp: Optional timestamp provided by the publisher.

    - Expirayion: life time for the message in a queue 

    - Delivery Mode: It can **Persistent** or **Transient**

        - Persistent: **written to disk** and if RabbitMQ service Restarts they are re-loaded 

        - Transient: if RabbitMQ service Restarts Messages are **Lost**

    - Priority: Priority of the message, Between 0-255

    - Message ID: Optinal unique message id set by the Publisher, to distinguish a message

    - Correlation: Optional id for matching a request and a response in remote procedure call (RPC) scenarios

    - Reply to: Optional queue or exchange name used in request-response scenarios

به طوری دیغالت همه چی روی رم هست و روی هارد بکاپ گرفته میشن
با دو روش میتونیم پیغام رو مسیر یابی کنیم با روتینگ کی و هدر


# Attributes of a queue

    - name: unique queue name, max 255 character UTF-8 string

    - Duable: whether to preserve or delete this queue when RabbitMQ restart                مهم وقتی ریستات بشه حذف شود یا ن

    - Auto Delete: whether to delete this queue if no on is subscibed to it                 مهم وقتی کسی ازش نخونه حذفش میکنه

    - Exclusibe: Used only by on connection and deleted when the connection is closed        بحث امنیت: وقتی کانکشنی بزنیم خودش ی صفی تولید میکنه و غیر اون کانکشن کسی دسترسی نداره و وقتی کانکشن قطع بشه صف رو حذف میکنه

    - Max Length: Maximum number of waiting message in a queue, overflow behavior can be set Drop the oldest message or reject the new message

    - Max Priority: Maximum number of priority value that this queue supports (Up to 255)

    - Message TTL: life time for each message that is added to this queue. if both message and queue had a TTL value, the lowest one will be chosen

    - Dead-letter Exchange: Name of the exchange that expired or dropped message will be automatically sent.

    - Binding Configurations: Associations between queues and exchanges. A queue must be bound to an exchange, in order to receive message from it. 


    - Lazy mode: if set true save in Hard (save on ram by default)
# Attributes of a Exchange

    - Name: Unique name of the exchange

    - Type: Type of the exchange. it can be, "fanout" "direct" "topic" "headers"

        - Fanout: هر پیغامی براش بیاد کپی میگیره و به تموم صف هایی ک بهش متصله میفرسته

        - Direct

        - Topic:
            
            - Use routing key in order to route a message, but does not require full match, check the pattern instead

            - Checks whether the routing key "pattern" of a queue match the received message's routing key.

            - Routing key of a queue can contain wild cards for matching message's routing key.

            - *.image :  convert.image داخل این تاپیک ارسال بشه و فقط یک دات رو پوشش میده

            - image.# :  هرچی ک اولش ایمیج بود رو ارسال کنه و تعداد دات ها مهم نیست

        - Headers:
        
            Use message headers in order to route a message to the bound queues.

            Ignore the routing key value of the message

            A message may have many different headers with different values.

            While binding to this type of exchange, every queue specifies which headers a message mau contain and whether it requires "all" or "any" of them to be exist is the message.



    - Durability: Same as queue durability.  Durable exchange survive after a service restart           بعد از ریستارت کردن بمونه یا نه

    - Auto Delete: if "true", exchange will be deleted when there is no bound queue left

    - Inrernal: Internal exchanges can be only receive message from other exchange

    - Alternate ExchangeL The name of the exchange that unrouteable message will be sent

    - Othe Arguments (x-arguments): Othe name arguments or setting that can be provided when creating an exchange. These names start with "x-", so these arguments are also called "x-arguments"


# Advanced Exchange

    - When a new queue is created on a RabbitMQ system, it is implicitly bound to a system exchange called "default exchange", with a routing key which is the same as the queue name

    - Default exchange has no name (empty string).

    - The type of deafult exchange is "direct".

    - When sending a message, if exchange name is left empty, it is handled by the "default exchange"

# Exchange to Exchange Binding

    - like binding a queue to an exchange, it is possible to bind an exchange to another exchange

    - Binding and message routing rules are the same

    - When an exchange is bound tyo another exchange, message from the source exchange are routed to the destination exchange using the binding configuration.

    - Finally, destination exchange routes these message to its bound queues.

# Alternate Exchange

    - Some of the message that are published to an exchange may not be suitble to route to any of the bound queues.

    - These are unrouted message.

    - They are discarded by the exchange, so they are lost

    - in order to collect these message, an "alternate exchange" can be defined for any exchange.


# Messaging Pattern

    - 

    - 

    -

# Push vs Pull

    - Tow main approaches for getting message from a queue




    - Push:

        - Consumer application subscribes to the queue and wait for message.

        - if there is already a message on the queue or when a new message arrives, it is automatically sent (pushed) to the consumer application.

        - This is the suggested way of getting message from a queue.

        - برای سرویس هایی ک سینک هستند بهتره از پوش مدل استفاده بشه 


    - Pull:
        - Consumer application does not subscribe to the queue but it constantly checks (polls) the queue for new message.

        - if there is a message available on the queue, it is manually fetched (pulled) by the consumer application.

        - Even though the pull mode is not recommended, it is the only solution when there is no live connection between message broker and consumer application.

        - در سرویس هایی ک سینک بودن مهم نیست و شب به شب نیاز هست متصل بشه به ظور مثال لاگی رو بگیره و پردازش انجام بشه و سرویس قطع بشه از پول استفاده میشه




# Publish - Subscribe

    - Publish-subscribe pattern is used to deliver the same message to all the subscribers

    - There may be one or more subscribes. in publish-subscribe pattern, there is one seperate queue for each subscriber.

    - Message is delicered ti each of these queues. so, each subscriber gets a copy of the same message.

    - this pattern is mostl used for publishing event notifications.


# Request - Reply

    - crolation id



# Priority Queues

    - All the message or task may not have same urgency level. Some of them may be very urgent while other may be processed if there is no other message.

    - Between 0 - 255    هر چی عدد بالاتر اولویت بالاتره

    - موقع تعریف کیو باید اولویت برای صف تعریف شده باشه تا برای پیام ها بتونیم اولویت های متفاوت تعریف کنیم اگر تو صف تعریف نشده باشه اولویت کار نمیکنه

        - Arguments: x-max-priotity = 5 Number

# Scaling Out

# Scale Out with Competing Consumers


# Consistent Hashing Exchange

    - Partition messages across queue via hashing function over routing key, message header or message property

    - به صورت دیفالت نیست و با پلاگین باید فعال بشه

    - وقتی پلاگین اضافه بشه داخل اکسچنج داخل بخش تایپ اضافه میشه

# Sharding Plugin and Modulus Exchange

    - partition messages across queues over multiple hosts via hashing function on the routing key


# Installation

    - 5672: For sending and receiing messages
    - 15672: For Management web interface

   Enable management plugins with run following command ( FOR WINDOWS )
    
    # rabbitmq-plugins enable rabbitmq_managements

# Docker

    # docker run -it --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3.11-management


# Clustering

    - https://github.com/pardahlman/docker-rabbitmq-cluster

    - https://github.com/oprearocks/RabbitMQ-Docker-cluster

    - https://github.com/oprearocks/RabbitMQ-Docker-cluster


   On UNIX systems, the cookie will be typically located in **/var/lib/rabbitmq/.erlang.cookie**
   - XKLUWXENGUEVPBGQTJXZ


    - Node names in a cluster must be unique.
        - rabbit1@hostname
        - rabbit2@hostname
    - When a node starts up, it checks whether it has been assigned a node name
# NOTE
خوبه برای تمام اکسچنج ها الترنیت اکسچنج مجزا بزاریم ک اگر پیامی قابل مسیریابی نبود رو اونجا دریافت و مدیریت و مانیتورینگ بکنیم

بهتره التراکسچنج رو فن اوت بزاریم ک مطمئن بشیم ک پیام به عبور کنه ازش








# Create Cluster

    # sudo docker run -d --net rabbitmq --hostname rabbit-1 --name rabbit-1 rabbitmq:3.11
    # sudo docker exec -it rabbit-1 cat /var/lib/rabbitmq/.erlang.cookie
        - Copy erlang code


# Join to Cluster

    Node 2  
      docker exec -it rabbit-2 rabbitmqctl stop_app
      docker exec -it rabbit-2 rabbitmqctl reset
      docker exec -it rabbit-2 rabbitmqctl join_cluster rabbit@rabbit-1
      docker exec -it rabbit-2 rabbitmqctl start_app
      docker exec -it rabbit-2 rabbitmqctl cluster_status
      
      
    Node 3      
      docker exec -it rabbit-3 rabbitmqctl stop_app
      docker exec -it rabbit-3 rabbitmqctl reset
      docker exec -it rabbit-3 rabbitmqctl join_cluster rabbit@rebbit-1
      docker exec -it rabbit-3 rabbitmqctl start_app
      docker exec -it rabbit-3 rabbitmqctl cluster_status
