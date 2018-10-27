sudo rabbitmqctl list_queues > queues.txt
OIFS=$IFS
IFS=$'\n'
replaceString=""
for queue in $(cat queues.txt); do
        replaced="${queue/game_/$replaceString}"
        if [[ $queue != $replaced ]]
        then
                IFS=$OIFS
                queue_name=( $queue )
                queue_name=${queue_name[0]}
                echo Deleting queue = $queue_name
                sudo rabbitmqctl delete_queue $queue_name
                IFS=$'\n'
        fi
done
rm queues.txt