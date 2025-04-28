workspace {
    name "Social network"
    
    model {
        user = person "User"
        moderator = person "Moderator"
        admin = person "Admin"

        socialNetwork = softwareSystem "Social network" {
            service = container "Service" {

                description "Handles users, posts, and messages"
                technology "python"

                // HTTP API
                apiGateway = component "API Gateway" {
                description "Handles HTTP requests and routes them to the service"
                technology "Flask"
                }


                userComponent = component "User component" {
                    description "Handles user registration and retrieval"
                    technology "FastAPI/Flask"
                }

                postComponent = component "Post component" {
                    description "Handles post creation and retrieval"
                    technology "FastAPI/Flask"
                }

                messageComponent = component "Message component" {
                    description "Handles sending and receiving messages"
                    technology "FastAPI/Flask"
                }
            }

            // Database
            database = container "Database" {
                technology "PostgreSQL"
            }

            // Caching
            cacheService = container "Cache service" {
                description "Handles caching for faster data retrieval"
                technology "Redis"
            }

            // Monitoring
            metricsCollector = container "Metrics collector" {
                description "Collects metrics for system monitoring"
                technology "Prometheus"
            }

            metricsVisualizer = container "Metrics visualizer" {
                description "Visualizes monitoring data"
                technology "Grafana"
            }
            
            apiGateway -> userComponent
            apiGateway -> messageComponent
            apiGateway -> postComponent

            service -> database "Reads/Writes data"
            service -> cacheService "Stores/Retrieves cached data"
            service -> metricsCollector "Sends metrics"
            metricsCollector -> metricsVisualizer "Provides monitoring data"

            user -> apiGateway "Uses social network features via HTTP"
            moderator -> socialNetwork "Reviews content"
            admin -> socialNetwork "Manages system"
        }
    }

    

    views {
        systemContext socialNetwork {
            include *
            autolayout lr
        }

        container socialNetwork {
            include *
            autolayout lr
        }

        component service {
            include *
            autoLayout lr
        }

        dynamic socialNetwork "SendMessage" {
            user -> service "Sends message request"
            service -> database "Writes message"
            database -> service "Message saved"
            service -> user "Message saved"
            service -> cacheService "Caches recent messages"
        }
    }
}