FROM crate:4.8.1

ENV CRATE_HEAP_SIZE=2g
RUN chgrp -R 0 /crate && chmod -R g=u /crate

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["crate"]